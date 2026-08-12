import os
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "customer_store.db")


def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建高仿真用户特征画像表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            preference TEXT,
            risk_level TEXT
        )
    """)

    # 创建商超产品信息表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            price REAL
        )
    """)

    # 创建1000条级高并发测试订单交易流水表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            product_id TEXT,
            status TEXT,
            amount REAL,
            created_at TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY(product_id) REFERENCES products(product_id)
        )
    """)

    # 填充200条种子客户画像
    categories = ["数码家电", "美妆护肤", "户外运动", "食品生鲜", "图书影音"]
    for i in range(1, 201):
        c_id = f"CUST_{i:03d}"
        pref = random.choice(categories)
        cursor.execute(
            "INSERT INTO customers VALUES (?, ?, ?, ?)",
            (c_id, f"客户_{i}", pref, random.choice(["低", "中", "高"])),
        )

    # 建立多模态标准产品库
    prod_titles = {
        "数码家电": [
            "降噪耳机",
            "智能手表",
            "机械键盘",
            "4K显示器",
            "电推剪",
            "无线鼠标",
        ],
        "美妆护肤": ["保湿面霜", "防晒喷雾", "精华液", "洁面乳", "润唇膏", "眼霜"],
        "户外运动": ["冲锋衣", "登山杖", "露营帐篷", "运动水壶", "筋膜枪", "跑步鞋"],
        "食品生鲜": [
            "黑咖啡",
            "全麦面包",
            "坚果礼盒",
            "即食鸡胸肉",
            "燕麦片",
            "生鲜牛排",
        ],
        "图书影音": [
            "算法导论",
            "设计模式",
            "大语言模型指南",
            "历史的温度",
            "科幻世界",
            "黑客与画家",
        ],
    }

    prod_id_counter = 1
    prod_list = []
    for cat, titles in prod_titles.items():
        for title in titles:
            p_id = f"PROD_{prod_id_counter:03d}"
            price = round(random.uniform(20.0, 2500.0), 2)
            cursor.execute(
                "INSERT INTO products VALUES (?, ?, ?, ?)", (p_id, title, cat, price)
            )
            prod_list.append((p_id, price))
            prod_id_counter += 1

    # 生成1000条具有真实时间梯度和业务状态的订单历史
    statuses = ["已下单", "已发货", "已签收", "退款中", "已退款"]
    start_date = datetime.now() - timedelta(days=90)

    for i in range(1, 1001):
        o_id = f"ORD_{i:05d}"
        c_id = f"CUST_{random.randint(1, 200):03d}"
        p_id, price = random.choice(prod_list)
        status = random.choice(statuses)
        order_date = start_date + timedelta(seconds=random.randint(0, 90 * 24 * 3600))
        cursor.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
            (o_id, c_id, p_id, status, price, order_date.strftime("%Y-%m-%d %H:%M:%S")),
        )

    conn.commit()
    conn.close()
    print(f"成功在本地构建测试数据库! 路径: {DB_PATH}")


if __name__ == "__main__":
    init_db()
