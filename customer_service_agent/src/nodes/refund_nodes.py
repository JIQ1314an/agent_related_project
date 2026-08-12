from langchain_core.messages import AIMessage
from langgraph.types import interrupt
from src.state import AgentState
from src.logger import agent_logger
from src.database import get_db_connection


def refund_node(state: AgentState):
    agent_logger.info("=== 进入退款审查子图 ===")
    order_id = state.get("current_order_id")

    if not order_id:
        return {"messages": [AIMessage(content="申请退款前，请告知您的订单号。")]}

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT order_id, amount, status FROM orders WHERE order_id = ?", (order_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "messages": [AIMessage(content=f"未找到订单 {order_id}，无法发起退款。")]
        }

    amount = row[1]
    order_status = row[2]

    if order_status == "已退款":
        return {
            "messages": [AIMessage(content="该订单系统显示已完成退款，无需重复发起。")]
        }

    # 核心面试加分项：大额资产变动触发 Human-in-the-Loop 阻断
    if amount > 1000.0:
        agent_logger.warning(
            f"检测到高额退款申请! 金额: ¥{amount}。触发 Human-in-the-Loop 机制阻断。"
        )

        # 抛出中断，挂起当前 Thread 状态机
        review_response = interrupt(
            {
                "reason": "HighAmountRefundReviewRequired",
                "order_id": order_id,
                "amount": amount,
                "prompt": f"订单 {order_id} 申请退款金额达 ¥{amount}，超出免审额度，需要人工审批。",
            }
        )

        # 恢复状态机后，捕获外部输入的人工审核状态
        is_approved = review_response.get("approved", False)
        agent_logger.info(f"人工审核完毕，结果为: {'批准' if is_approved else '拒绝'}")

        if is_approved:
            return execute_db_refund(order_id, amount)
        else:
            return {
                "messages": [
                    AIMessage(content=f"您的订单 {order_id} 的退款申请未通过人工审核。")
                ]
            }

    agent_logger.info(f"小额退款自动处理成功。金额: ¥{amount}")
    return execute_db_refund(order_id, amount)


def execute_db_refund(order_id: str, amount: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET status = '已退款' WHERE order_id = ?", (order_id,)
    )
    conn.commit()
    conn.close()
    return {
        "messages": [
            AIMessage(
                content=f"退款处理完成！订单 {order_id} 的退款金额 ¥{amount} 已原路退回。"
            )
        ]
    }
