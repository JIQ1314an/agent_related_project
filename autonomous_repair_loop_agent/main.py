from agent import AutonomousLoopAgent
from evaluator import AgentEvaluator
from logger import logger

# 一个包含典型逻辑错误的快速排序实现
BUGGY_QUICKSORT_CODE = """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[0]
    # 逻辑错误：遗漏了与 pivot 相等的元素处理，导致递归死循环/死锁
    left = [x for x in arr if x < pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + [pivot] + quicksort(right)
"""

UNIT_TEST_CODE = """
import unittest

class TestQuickSort(unittest.TestCase):
    def test_sorted_array(self):
        self.assertEqual(quicksort([3, 6, 8, 10, 1, 2, 1]), [1, 1, 2, 3, 6, 8, 10])
        self.assertEqual(quicksort([]), [])
        self.assertEqual(quicksort([5, 5, 5, 5]), [5, 5, 5, 5])

if __name__ == '__main__':
    unittest.main()
"""


def main():
    logger.info("启动应用入口 Demo：自主代码 Bug 修复...")

    agent = AutonomousLoopAgent()
    evaluator = AgentEvaluator()

    # exit()  # 测试Langfuse SDK是否成功
    # 启动 Loop Agent 自主修复
    result = agent.run_autonomous_fix_loop(
        initial_code=BUGGY_QUICKSORT_CODE, test_code=UNIT_TEST_CODE
    )

    # 评估与结果打印
    if result["success"]:
        logger.info("\n✅ 代码修复成功！生成的生产级代码如下：")
        print("--------------------------------------------------")
        print(result["final_code"])
        print("--------------------------------------------------")
    else:
        logger.error("\n❌ 代码修复失败，达到最大重试次数上限。")

    # 计算量化指标
    metrics = evaluator.evaluate_repair_job(result, max_allowed_steps=5)
    print(f"\n[任务评测得分总结]: {metrics}")


if __name__ == "__main__":
    main()
