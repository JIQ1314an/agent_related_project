# main.py
from anyio import Path

from pathlib import Path

from sql_generator import get_db_schema_for_tables, generate_sql, execute_sql

# InvoiceLine（订单明细） --> Invoice_Items
# 修正映射后的测试用例
test_cases = [
    {
        "id": 1,
        "difficulty": "简单",
        "question": "一共有多少个客户？",
        "expected_tables": ["Customers"],
    },
    {
        "id": 2,
        "difficulty": "简单",
        "question": "列出所有来自德国的客户",
        "expected_tables": ["Customers"],
    },
    {
        "id": 3,
        "difficulty": "中等",
        "question": "哪个员工处理的订单最多？",
        "expected_tables": ["Employees", "Invoices", "Customers"],
    },
    {
        "id": 4,
        "difficulty": "中等",
        "question": "每个类别（流派）有多少产品（歌曲）？按数量降序排列",
        "expected_tables": ["Tracks", "Genres"],
    },
    {
        "id": 5,
        "difficulty": "复杂",
        "question": "消费最高的前5个客户及他们的总消费金额是多少？",
        "expected_tables": ["Customers", "Invoices"],
    },  # 剔除了2024年Q1的时间限制，因为Chinook老数据多在2009-2013
    {
        "id": 6,
        "difficulty": "复杂",
        "question": "从未被购买的产品（歌曲）有哪些？",
        "expected_tables": ["Tracks", "Invoice_Items"],
    },
    {
        "id": 7,
        "difficulty": "复杂",
        "question": "按月统计所有的销售额趋势",
        "expected_tables": ["Invoices"],
    },
    {
        "id": 8,
        "difficulty": "中等",
        "question": "购买了3种以上不同产品（歌曲）的客户有哪些？",
        "expected_tables": ["Customers", "Invoices", "Invoice_Items"],
    },
]


def run_benchmark():

    passed_count = 0

    current_dir = Path(__file__).resolve().parent
    db_path = current_dir / "chinook.db"

    print("开始 Text-to-SQL 智能生成器评测...\n" + "=" * 50)

    for case in test_cases[2:3]:  # 仅测试第3个用例，避免频繁调用大模型消耗 token
        print(f"\n[用例 {case['id']}] ({case['difficulty']}) 问: {case['question']}")

        # 1. LLM 生成
        schema = get_db_schema_for_tables(case["expected_tables"], db_path)
        # print(f"🔍 仅提供相关表的 Schema:\n{schema}\n")
        result = generate_sql(case["question"], schema)
        print(f"🤖 思考: {result.thought}")
        print(f"💻 SQL: {result.sql_query}")

        # 2. 执行验证
        exec_res = execute_sql(result.sql_query, db_path)

        if exec_res["success"]:
            print(f"✅ 执行成功！返回了 {len(exec_res['data'])} 条数据。")
            # 简单验证表是否命中（不绝对，但可以作为指标之一）
            # 完美的验收需要人工核对数据或比对标准答案数据
            passed_count += 1
        else:
            print(f"❌ 执行失败。报错原因: {exec_res['error']}")

        # break

    accuracy = (passed_count / len(test_cases)) * 100
    print("\n" + "=" * 50)
    print(f"📊 评测结束。最终正确率（成功执行率）: {accuracy:.2f}%")


if __name__ == "__main__":
    run_benchmark()
