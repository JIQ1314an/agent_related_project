import sqlite3
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from config.settings import AM_PATH
from src.state import AgentState
from src.nodes import (
    intent_classifier_node,
    general_node,
    order_query_node,
    refund_node,
    recommend_node,
)


def router_edge(
    state: AgentState,
) -> Literal["order_query_node", "refund_node", "recommend_node", "general_node"]:
    """
    根据意图节点的决策变量状态进行条件边分发
    """
    action = state.get("next_action")
    if action in ["order_query", "refund", "recommend", "general"]:
        return f"{action}_node"
    return "general_node"


# 实例化状态机容器
workflow = StateGraph(AgentState)

# 挂载全量离线原子节点
workflow.add_node("intent_classifier_node", intent_classifier_node)
workflow.add_node("order_query_node", order_query_node)
workflow.add_node("refund_node", refund_node)
workflow.add_node("recommend_node", recommend_node)
workflow.add_node("general_node", general_node)

# 构建状态机树形流转关系
workflow.add_edge(START, "intent_classifier_node")

# 绑定核心条件路由逻辑
workflow.add_conditional_edges(
    "intent_classifier_node",
    router_edge,
    {
        "order_query_node": "order_query_node",
        "refund_node": "refund_node",
        "recommend_node": "recommend_node",
        "general_node": "general_node",
    },
)

# 各叶子业务子系统节点执行完毕后流转至图终点
workflow.add_edge("order_query_node", END)
workflow.add_edge("refund_node", END)
workflow.add_edge("recommend_node", END)
workflow.add_edge("general_node", END)

# # 内置单机级高可靠内存状态 Checkpointer，确保可以随线程挂起和恢复
# memory_checkpointer = MemorySaver()
# compiled_app = workflow.compile(checkpointer=memory_checkpointer)

#  Checkpointing 持久化
# 1. 创建或连接到一个本地的 SQLite 数据库文件（持久化到硬盘）
conn = sqlite3.connect(AM_PATH, check_same_thread=False)
db_storage = SqliteSaver(conn)
# 2. 编译图，将内存替换为数据库持久化
compiled_app = workflow.compile(checkpointer=db_storage)
