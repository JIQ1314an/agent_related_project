from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    统一 LangGraph 跨节点传递的高级状态机机 Schema。
    """

    # 消息全量历史追加列表，基于 add_messages 机制自动合并消息流
    messages: Annotated[List[AnyMessage], add_messages]

    # 状态路由决策变量
    next_action: Optional[
        str
    ]  # 可选值: "order_query" | "refund" | "recommend" | "general"

    # 上下文跨节点插槽抽取槽位
    current_order_id: Optional[str]
    current_customer_id: Optional[str]
    refund_amount: Optional[float]
    refund_approved: Optional[bool]

    # 也可以配置其他状态，不如orders_id、customers_id...
