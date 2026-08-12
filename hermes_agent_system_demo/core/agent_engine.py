import json
from typing import List, Dict, Any
from core.llm_client import QwenLLMClient
from skills.skill_manager import SkillManager
from config import config
from logger import logger, log_step, log_error

class HermesAgentEngine:
    """Hermes 风格的单体自主 ReAct Agent 引擎"""

    def __init__(self, llm_client: QwenLLMClient, skill_manager: SkillManager):
        self.llm = llm_client
        self.skill_manager = skill_manager
        self.system_prompt = (
            "你是一个具备自主学习与能力进化的 Hermes 智能 Agent。"
            "你可以使用系统提供的 Tool/Skill 解决复杂问题。"
            "在回答时，遵循 ReAct 范式：逐步思考，精确调用工具，拿到结果后再给出最终严谨的结论。"
        )

    def run(self, user_query: str) -> str:
        """执行 ReAct 主循环"""
        log_step("AgentEngine.start", f"收到用户目标 Query: {user_query}")
        
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]

        iteration = 0
        while iteration < config.MAX_ITERATIONS:
            iteration += 1
            log_step(f"ReAct Loop #{iteration}", f"进入第 {iteration} 轮迭代...")

            current_tools = self.skill_manager.get_all_schemas()
            response_msg = self.llm.chat_with_tools(messages=messages, tools=current_tools if current_tools else None)

            # 修复：使用 model_dump() 转换为字典存入 messages 历史，保证数据格式的一致性与 SDK 兼容性
            messages.append(response_msg.model_dump())

            tool_calls = getattr(response_msg, "tool_calls", None)

            if not tool_calls:
                final_answer = response_msg.content
                log_step("ReAct Loop Complete", f"Agent 得出最终结论:\n{final_answer}")
                return final_answer

            for tool_call in tool_calls:
                func_name = tool_call.function.name
                call_id = tool_call.id
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception as e:
                    log_error("AgentEngine.parse_args", f"解析工具参数失败: {str(e)}")
                    args = {}

                log_step("AgentEngine.ToolCallNode", f"触发工具调用 ID: {call_id}\n工具名: {func_name}\n参数: {json.dumps(args, ensure_ascii=False)}")

                execution_result = self.skill_manager.execute_skill(func_name, args)

                # 修复：格式化为 OpenAI API 标准 tool response message
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(execution_result, ensure_ascii=False)
                })

        log_error("AgentEngine.run", "达到最大迭代上限，程序强制退出。")
        return "很抱歉，任务在最大步数内未执行完成。"