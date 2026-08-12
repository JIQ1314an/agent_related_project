import os
import sys
from pathlib import Path

# 全局入口根路径强制注入
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.repair_loop import AutonomousRepairAgent
from observability import telemetry

if __name__ == "__main__":
    buggy_task_description = (
        "实现一个函数 process_user_data(data_list)，接收字典列表，提取所有用户的 'age' 属性并计算平均年龄。"
        "要求：如果 data_list 为空或列表中存在缺少 'age' 键的元素，需跳过该非法元素而不是报错崩溃。"
    )

    faulty_code = """
def process_user_data(data_list):
    total_age = 0
    # 语法错误：缺少冒号
    for item in data_list
        total_age += item['age']
    return total_age / len(data_list)

test_data = [{'name': 'Alice', 'age': 25}, {'name': 'Bob'}, {'name': 'Charlie', 'age': '30'}]
print("Result:", process_user_data(test_data))
"""

    agent = AutonomousRepairAgent(task_id="PROD_FIX_001")

    try:
        result = agent.run_repair_loop(
            task_description=buggy_task_description, buggy_code=faulty_code
        )
        print("\n================== 运行结果汇总 ==================")
        print(f"最终修复状态: {'成功' if result['success'] else '失败'}")
        print(f"迭代修复轮数: {result['attempts']}")
        print("修复后的代码:\n")
        print(result["final_code"])
    finally:
        telemetry.flush()
