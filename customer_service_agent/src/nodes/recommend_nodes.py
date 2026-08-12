from langchain_core.messages import AIMessage
from src.state import AgentState
from src.logger import agent_logger
from src.database import get_db_connection


def recommend_node(state: AgentState):
    agent_logger.info("=== 进入产品推荐子图 ===")
    customer_id = state.get("current_customer_id")

    # 兜底默认用户
    if not customer_id:
        customer_id = "CUST_001"

    conn = get_db_connection()
    cursor = conn.cursor()

    # 模拟 RAG / 向量召回的第一步：精准提取本地用户画像及消费偏好标签
    cursor.execute(
        "SELECT preference FROM customers WHERE customer_id = ?", (customer_id,)
    )
    pref_row = cursor.fetchone()
    pref = pref_row[0] if pref_row else "数码家电"

    # 模拟协同过滤推荐机制，根据用户标签实时检索热销商品库
    cursor.execute(
        "SELECT title, price FROM products WHERE category = ? LIMIT 3", (pref,)
    )
    products = cursor.fetchall()
    conn.close()

    recommendations = "\n".join([f"· 【{p[0]}】 售价: ¥{p[1]}" for p in products])
    reply = f"根据您的消费偏好，专属为您挑选了以下【{pref}】品类的爆款好物：\n{recommendations}"
    return {"messages": [AIMessage(content=reply)]}
