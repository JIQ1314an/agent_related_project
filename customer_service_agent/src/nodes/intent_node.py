# src/nodes/intent_node.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from langchain_core.prompts import PromptTemplate

# 【核心重构】：引入标准 Pydantic 输出解析器，彻底停用 black-box 的 with_structured_output
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from config.settings import MODEL_NAME, API_BASE, DASHSCOPE_API_KEY
from src.state import AgentState
from src.logger import agent_logger


# 1. 客观、纯净的 Schema 定义，不夹杂任何偏袒模型的特殊补丁
class IntentSchema(BaseModel):
    intent: Literal["order_query", "refund", "recommend", "general"] = Field(
        description="User core intent category."
    )
    order_id: Optional[str] = Field(
        None,
        description="Explicit order ID extracted from the text, e.g., 'ORD_00005'. Return null if not present.",
    )
    customer_id: Optional[str] = Field(
        None,
        description="Explicit customer ID extracted from the text, e.g., 'CUST_001'. Return null if not present.",
    )


# 2. 初始化最纯净的大模型客户端，不携带任何隐藏的 response_format 或 tool_choice 污染
llm = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0,
    openai_api_base=API_BASE,
    openai_api_key=DASHSCOPE_API_KEY,
)

# 3. 实例化标准解析器
parser = PydanticOutputParser(pydantic_object=IntentSchema)


def intent_classifier_node(state: AgentState):
    agent_logger.info("=== 进入意图识别节点 ===")
    if not state["messages"]:
        return {"next_action": "general"}

    last_message = state["messages"][-1].content

    # 4. 构建标准显式 Prompt 模板。
    # parser.get_format_instructions() 会自动将 Pydantic 结构完美转化为标准、严谨的结构化输出说明。
    prompt_template = PromptTemplate(
        template=(
            "你是一个电商客服数据提取专家。请分析以下用户对话，并严格按照格式说明输出对应的 JSON 对象。\n\n"
            "{format_instructions}\n\n"
            "用户对话内容: {user_input}\n"
        ),
        input_variables=["user_input"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # 5. 组装一条清晰、透明的声明式 LangChain 表达式（LCEL）
    chain = prompt_template | llm | parser

    try:
        # 此时，Qwen 能够无拘无束地在 <think> 中完成高精准的槽位对齐与提取，然后稳健输出 JSON
        result = chain.invoke({"user_input": last_message})
        agent_logger.info(
            f"意图分类成功: {result.intent} | 关联订单: {result.order_id} | 关联客户: {result.customer_id}"
        )
        # ==================================================================
        # 日志输出，调试使用
        # agent_logger.info(f"Input，意图分类原始last_message: {last_message}")
        # agent_logger.info(f"Output，意图分类结果: {result.json()}")
        # ==================================================================

        return {
            "next_action": result.intent,
            "current_order_id": (
                result.order_id if result.order_id else state.get("current_order_id")
            ),
            "current_customer_id": (
                result.customer_id
                if result.customer_id
                else state.get("current_customer_id")
            ),
        }
    except Exception as e:
        agent_logger.error(f"意图分类发生异常: {str(e)}")
        # 容灾兜底
        return {"next_action": "general"}


def general_node(state: AgentState):
    agent_logger.info("=== 进入通用兜底节点 ===")
    last_message = state["messages"][-1].content
    prompt = f"你是一个高情商全能电商客服，同时避免胡编乱造，回答客观。请热情、简洁地回复以下用户日常问询：\n{last_message}"
    response = llm.invoke(prompt, config={"configurable": {"temperature": 0.7}})
    return {"messages": [response]}
