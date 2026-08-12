import os
import sys
from pathlib import Path

# 路径防错注入：自动向上查找两级，定位根目录并注入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import time
from typing import Dict, Any
from openai import OpenAI
from config import config
from logger import get_task_logger
from observability import telemetry
from tools.code_runner import PythonSandbox, ExecutionResult
from langfuse import observe


class AutonomousRepairAgent:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.log = get_task_logger(task_id, step="REPAIR_LOOP")
        self.client = OpenAI(api_key=config.QWEN_API_KEY, base_url=config.QWEN_BASE_URL)

    def _extract_code(self, response_text: str) -> str:
        pattern = r"```python\n(.*?)\n```"
        matches = re.findall(pattern, response_text, re.DOTALL)
        if matches:
            return matches[-1].strip()
        pattern_fallback = r"```\n(.*?)\n```"
        fallback_matches = re.findall(pattern_fallback, response_text, re.DOTALL)
        return (
            fallback_matches[-1].strip() if fallback_matches else response_text.strip()
        )

    # 关键：添加 @observe 装饰器，Langfuse 才会自动把这个函数当成一个 Trace 记录
    @observe(name="Autonomous_Repair_Loop")
    def run_repair_loop(
        self, task_description: str, buggy_code: str = ""
    ) -> Dict[str, Any]:
        history_context = []
        current_code = buggy_code
        attempts = 0
        success = False
        final_result = None

        self.log.info(f"开启 Loop 任务处理: {task_description[:50]}...")

        while attempts < config.MAX_REPAIR_ATTEMPTS and not success:
            attempts += 1
            step_log = get_task_logger(self.task_id, step=f"LOOP_ATTEMPT_{attempts}")
            step_log.info(f"第 {attempts}/{config.MAX_REPAIR_ATTEMPTS} 次自主尝试...")

            if attempts == 1 and not buggy_code:
                system_prompt = "你是一个精通Python的严谨工程师。实现需求并将完整代码包裹在 ```python ... ``` 中。"
                user_prompt = f"任务描述: {task_description}"
            else:
                system_prompt = "你是一个高级调试专家。分析 Traceback 报错，修复 Bug 并返回完整代码。"
                user_prompt = (
                    f"任务描述: {task_description}\n\n"
                    f"历史尝试代码:\n```python\n{current_code}\n```\n\n"
                    f"上一次报错 (stderr):\n{final_result.stderr if final_result else 'None'}\n\n"
                    f"输出 (stdout):\n{final_result.stdout if final_result else 'None'}\n\n"
                    "请修正错误并提供完整 Python 代码："
                )

            # 调用 Qwen3.7-Plus
            completion = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            raw_response = completion.choices[0].message.content
            tokens_used = {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens,
            }

            # 安全日志打标
            telemetry.log_generation(
                task_id=self.task_id,
                name=f"Qwen_Attempt_{attempts}",
                input_prompt=user_prompt,
                output_text=raw_response,
                usage=tokens_used,
                model=config.MODEL_NAME,
            )

            current_code = self._extract_code(raw_response)
            step_log.info("代码提取完成，进入沙盒环境执行...")

            exec_result = PythonSandbox.run_code(
                current_code, timeout=config.EXECUTION_TIMEOUT
            )
            final_result = exec_result

            if exec_result.success:
                success = True
                step_log.info(
                    f"✅ 执行成功! 耗时: {exec_result.duration_ms}ms | Stdout: {exec_result.stdout.strip()}"
                )
            else:
                step_log.warning(
                    f"❌ 运行报错 (Exit Code {exec_result.exit_code}):\n{exec_result.stderr.strip()}"
                )

            history_context.append(
                {
                    "attempt": attempts,
                    "code": current_code,
                    "success": exec_result.success,
                    "stderr": exec_result.stderr,
                    "stdout": exec_result.stdout,
                }
            )

        return {
            "success": success,
            "attempts": attempts,
            "final_code": current_code,
            "exec_result": final_result,
            "history": history_context,
        }
