import re
from typing import Dict, Any, Tuple
from openai import OpenAI
from config import settings
from logger import logger
from sandbox import CodeSandbox
from observability import obs_manager


class AutonomousLoopAgent:
    def __init__(self):
        self.model_name = getattr(settings, "MODEL_NAME", "qwen3.7-plus")
        self.sandbox = CodeSandbox()
        self.system_prompt = (
            "你是一名首席 AI 架构师和高级 Python 软件工程师。"
            "请根据传入的代码、测试用例以及报错日志进行 Bug 修复。"
            "请务必只输出修复后的完整 Python 代码，包裹在 ```python ... ``` 代码块中。"
        )
        self.openai_client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY, base_url=settings.QWEN_BASE_URL
        )

    @staticmethod
    def _extract_code(content: str) -> str:
        """
        安全提取 Markdown 代码块中的 Python 代码，若无代码块则返回原始内容
        """
        if not content:
            return ""
        pattern = r"```(?:python)?\s*\n?(.*?)\n?```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content.strip()

    def run_autonomous_fix_loop(
        self, initial_code: str, test_code: str
    ) -> Dict[str, Any]:
        # 创建顶层业务 Trace
        trace = obs_manager.create_trace(
            name="Code_Repair_Task",
            input={"initial_code": initial_code, "test_code": test_code},
            metadata={
                "model": self.model_name,
                "max_iterations": settings.MAX_LOOP_ITERATIONS,
            },
        )

        current_code = initial_code
        iteration_history = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        is_fixed = False

        logger.info(
            "================== [START AUTONOMOUS REPAIR LOOP] =================="
        )

        for iteration in range(1, settings.MAX_LOOP_ITERATIONS + 1):
            logger.info(
                f"\n>>> [LOOP ITERATION {iteration}/{settings.MAX_LOOP_ITERATIONS}] <<<"
            )

            # ✅ 1. 【开始计时】在沙箱测试开始前创建 Span
            span_sb = trace.span(
                name=f"Iteration_{iteration}_Sandbox_Test",
                input={"code": current_code, "test_code": test_code},
            )

            # ✅ 2. 【真正耗时】执行沙箱代码测试
            test_result = self.sandbox.execute_test(current_code, test_code)

            # ✅ 3. 【结束计时】上报输出，使 Langfuse 能够精确捕获沙箱耗时
            span_sb.end(output=test_result)

            step_record = {
                "iteration": iteration,
                "code": current_code,
                "success": test_result["success"],
                "error_log": test_result["stderr"],
                "execution_time": test_result["execution_time"],
            }
            iteration_history.append(step_record)

            if test_result["success"]:
                logger.info(
                    f"🎉 [SUCCESS] 判定通过！代码在第 {iteration} 次循环修复成功！"
                )
                is_fixed = True
                break

            logger.warning(
                f"❌ [FAIL] 第 {iteration} 次测试不通过，正在触发 Agent 自主调优循环..."
            )

            try:
                new_code, usage = self._call_qwen_fix(
                    buggy_code=current_code,
                    test_code=test_code,
                    error_log=test_result["stderr"] or test_result["stdout"],
                    iteration=iteration,
                    trace=trace,
                )

                total_prompt_tokens += usage.get("prompt_tokens", 0)
                total_completion_tokens += usage.get("completion_tokens", 0)
                current_code = new_code

            except Exception as e:
                logger.critical(f"[CRITICAL AGENT ERROR] 模型调用过程异常: {str(e)}")
                break

        # 循环结束，给根 Trace 更新最终业务状态
        trace.update(
            output={
                "is_fixed": is_fixed,
                "total_iterations": len(iteration_history),
                "final_code": current_code,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
            }
        )
        obs_manager.flush()

        logger.info(
            "================== [FINISH AUTONOMOUS REPAIR LOOP] =================="
        )

        return {
            "success": is_fixed,
            "total_iterations": len(iteration_history),
            "final_code": current_code,
            "history": iteration_history,
            "token_stats": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
            },
        }

    def _call_qwen_fix(
        self,
        buggy_code: str,
        test_code: str,
        error_log: str,
        iteration: int,
        trace: Any = None,
    ) -> Tuple[str, dict]:
        prompt_messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"Buggy Code:\n{buggy_code}\n\nTest Code:\n{test_code}\n\nError Log:\n{error_log}",
            },
        ]

        gen = None
        if trace:
            gen = trace.generation(
                name=f"Iteration_{iteration}_Qwen_Fix",
                model=self.model_name,
                input=prompt_messages,
            )

        try:
            logger.info(
                f"[AGENT -> QWEN3.7-PLUS] 发起 LLM 修复请求 (Iteration: {iteration})"
            )

            response = self.openai_client.chat.completions.create(
                model=self.model_name, messages=prompt_messages, temperature=0.2
            )

            content = response.choices[0].message.content or ""
            new_code = self._extract_code(content)

            p_tokens = (
                getattr(response.usage, "prompt_tokens", 0) if response.usage else 0
            )
            c_tokens = (
                getattr(response.usage, "completion_tokens", 0) if response.usage else 0
            )
            t_tokens = (
                getattr(response.usage, "total_tokens", 0) if response.usage else 0
            )

            # 兼容各版本 Langfuse 的 Token 计数规范
            usage = {
                "input": p_tokens,
                "output": c_tokens,
                "total": t_tokens,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "total_tokens": t_tokens,
                "unit": "TOKENS",
            }

            if gen:
                gen.end(
                    output={"extracted_code": new_code, "raw_response": content},
                    usage=usage,
                )

            logger.info(
                f"[QWEN3.7-PLUS RESPONSE] Tokens used: {usage['total_tokens']} "
                f"(Prompt: {usage['prompt_tokens']}, Completion: {usage['completion_tokens']})"
            )
            return new_code, usage

        except Exception as e:
            if gen:
                gen.end(output={"error": str(e)})
            raise e
