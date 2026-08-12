from typing import Dict, Any, List, TypedDict, Annotated
import operator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from app.config import settings
from app.logger import logger
from app.harness.engine import HarnessEngine
from app.mcp.registry import mcp_registry


# 定义 LangGraph 的标准 State 状态拓扑
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    tenant_id: str
    current_loop: int
    max_loops: int
    validation_error: str
    execution_result: str
    is_completed: bool


class WorkflowCompiler:
    """
    将前端/API 传入的 JSON 工作流配置动态编译构建为可自治执行的 LangGraph StateGraph
    包含完整 Harness Loop 闭环机制
    """

    def __init__(self, json_config: Dict[str, Any]):
        self.config = json_config
        self.system_prompt = json_config.get(
            "system_prompt", "你是一个企业级 AI 助手。请按要求完成任务。"
        )
        self.allowed_tools = json_config.get("allowed_tools", [])

        # 初始化 国产模型 qwen3.7-plus API 接入
        self.llm = ChatOpenAI(
            model=settings.QWEN_MODEL_NAME,
            openai_api_key=settings.DASHSCOPE_API_KEY,
            openai_api_base=settings.QWEN_BASE_URL,
            temperature=0.1,
        )

    def build(self) -> StateGraph:
        """编译图逻辑拓扑"""
        builder = StateGraph(AgentState)

        # 注册节点
        builder.add_node("llm_reasoning", self._llm_reasoning_node)
        builder.add_node("harness_validation", self._harness_validation_node)
        builder.add_node("execute_mcp_tool", self._execute_mcp_tool_node)

        # 逻辑边绑定
        builder.set_entry_point("llm_reasoning")
        builder.add_edge("llm_reasoning", "harness_validation")

        # Harness 校验分支判断 (Loop 重试 / 执行工具 / 完结)
        builder.add_conditional_edges(
            "harness_validation",
            self._route_after_validation,
            {
                "retry_loop": "llm_reasoning",
                "call_tool": "execute_mcp_tool",
                "finish": END,
            },
        )
        builder.add_edge("execute_mcp_tool", "llm_reasoning")

        return builder.compile()

    def _llm_reasoning_node(self, state: AgentState) -> Dict[str, Any]:
        """节点 1：LLM 逻辑推理与决策"""
        loop_cnt = state.get("current_loop", 0) + 1
        logger.info(
            f"=== [Loop Node: Reasoning] 进入第 {loop_cnt} 次 Loop 推理循环 ==="
        )

        messages = [SystemMessage(content=self.system_prompt)] + state["messages"]

        # 如果前一轮有 Harness 校验失败反馈，注入系统重试提示词进行自愈
        if state.get("validation_error"):
            logger.warning(
                f"[Harness Loop Retry Prompt] 注入修正在第 {loop_cnt} 次循环中的错误: {state['validation_error']}"
            )
            messages.append(
                HumanMessage(
                    content=f"【System Notice - Output Validation Failed】\n上一步输出不符合要求：{state['validation_error']}\n请重新思考并严格按照要求输出标准 JSON 格式。"
                )
            )

        tools_desc = [
            mcp_registry.get_tool(t)
            for t in self.allowed_tools
            if t in mcp_registry._tools
        ]
        prompt_enhancement = f'\n你可使用的 MCP 工具定义如下:\n{tools_desc}\n若需要调用工具，请输出 JSON 格式: {{"action": "tool_name", "args": {{...}}}}\n若完成任务，请输出 JSON 格式: {{"action": "final_answer", "result": "最终答复"}}'

        messages[0].content += prompt_enhancement

        response = self.llm.invoke(messages)
        logger.info(f"[LLM Agent Response Output Raw]: {response.content}")

        return {
            "messages": [response],
            "current_loop": loop_cnt,
            "validation_error": "",  # 清理错误标志位
        }

    def _harness_validation_node(self, state: AgentState) -> Dict[str, Any]:
        """节点 2：Harness 控制层强校验"""
        logger.info(f"=== [Harness Node: Validation] 开启输入输出与结构校验 ===")
        last_message = state["messages"][-1].content
        harness = HarnessEngine(tenant_id=state.get("tenant_id", "default_tenant"))

        is_valid, parsed_data, err_msg = harness.validate_llm_output(last_message)

        if not is_valid:
            return {"validation_error": err_msg}

        action = parsed_data.get("action")
        if action == "final_answer":
            return {
                "is_completed": True,
                "execution_result": str(parsed_data.get("result")),
            }

        if action not in self.allowed_tools:
            return {
                "validation_error": f"不被允许的工具调用: [{action}]。仅允许调用: {self.allowed_tools}"
            }

        return {"is_completed": False, "execution_result": json.dumps(parsed_data)}

    def _route_after_validation(self, state: AgentState) -> str:
        """条件路由控制核心逻辑"""
        if state.get("validation_error"):
            if state.get("current_loop", 0) >= state.get(
                "max_loops", settings.MAX_LOOP_RETRIES
            ):
                logger.error(
                    f"[Loop Gateway Abort] 已达到最大重试上限 ({state['max_loops']})，直接终止流"
                )
                return "finish"
            return "retry_loop"

        if state.get("is_completed"):
            logger.info("[Loop Gateway] 任务完全求解并由 Harness 验证通过，流程结束")
            return "finish"

        return "call_tool"

    def _execute_mcp_tool_node(self, state: AgentState) -> Dict[str, Any]:
        """节点 3：MCP 工具安全沙箱执行"""
        logger.info(f"=== [Tool Node: Execution] 触发沙箱工具节点 ===")
        harness = HarnessEngine(tenant_id=state.get("tenant_id", "default_tenant"))

        tool_payload = json.loads(state["execution_result"])
        tool_name = tool_payload.get("action")
        tool_args = tool_payload.get("args", {})

        success, output = harness.execute_sandboxed_tool(tool_name, tool_args)

        feedback = f"【MCP Tool [{tool_name}] 执行结果】: {output}"
        logger.info(f"[Tool Execution Result Feedback]: {feedback}")

        return {"messages": [HumanMessage(content=feedback)]}
