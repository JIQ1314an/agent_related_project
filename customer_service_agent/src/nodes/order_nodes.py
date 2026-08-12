from langchain_core.messages import AIMessage
from src.state import AgentState
from src.logger import agent_logger
from src.database import get_db_connection


def order_query_node(state: AgentState):
    agent_logger.info("=== 进入订单查询子图 ===")
    order_id = state.get("current_order_id")

    # agent_logger.info(f"当前状态：{str(state)}")

    if not order_id:
        return {
            "messages": [
                AIMessage(content="请提供您需要查询的订单号（例如：ORD_00001）。")
            ]
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT order_id, status, amount, created_at FROM orders WHERE order_id = ?",
        (order_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        reply = f"为您查到订单 【{row[0]}】 当前状态为：*{row[1]}*。订单金额：¥{row[2]}，下单时间：{row[3]}。"
    else:
        reply = f"抱歉，系统未查到订单号为 【{order_id}】 的记录，请核对后重试。"

    return {"messages": [AIMessage(content=reply)]}
