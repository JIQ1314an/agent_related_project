import json
from agent import AutonomousLoopAgent
from evaluator import AgentEvaluator
from logger import logger

# 测试数据集：定义带 Bug 的代码和正确的单元测试用例
TEST_DATASET = [
    {
        "id": "task_01_lru_cache_bug",
        "description": "修复 LRU Cache 淘汰策略颠倒的 Bug",
        "buggy_code": """
class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        # 错误：获取值后未更新键访问顺序
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache[key] = value
        else:
            if len(self.cache) >= self.capacity:
                # 错误：Pop 了最先加入的元素而非最久未使用的元素
                first_key = next(iter(self.cache))
                del self.cache[first_key]
            self.cache[key] = value
""",
        "test_code": """
import unittest

class TestLRU(unittest.TestCase):
    def test_lru_behavior(self):
        cache = LRUCache(2)
        cache.put(1, 1)
        cache.put(2, 2)
        self.assertEqual(cache.get(1), 1)       # 访问 key 1，使得 key 2 成为最久未使用
        cache.put(3, 3)                         # 应淘汰 key 2
        self.assertEqual(cache.get(2), -1)      # key 2 应该被移除
        self.assertEqual(cache.get(3), 3)

if __name__ == '__main__':
    unittest.main()
""",
    },
    {
        "id": "task_02_binary_search_overflow",
        "description": "修复二分查找死循环与边界越界问题",
        "buggy_code": """
def binary_search(nums, target):
    left, right = 0, len(nums)
    # 错误：循环条件导致死循环
    while left < right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            # 错误：没有 +1 导致陷入死循环
            left = mid 
        else:
            right = mid - 1
    return -1
""",
        "test_code": """
import unittest

class TestBinarySearch(unittest.TestCase):
    def test_search(self):
        self.assertEqual(binary_search([1, 2, 3, 4, 5], 3), 2)
        self.assertEqual(binary_search([1, 2, 3, 4, 5], 6), -1)
        self.assertEqual(binary_search([1, 2, 3, 4, 5], 1), 0)

if __name__ == '__main__':
    unittest.main()
""",
    },
]


def run_batch_evaluation():
    agent = AutonomousLoopAgent()
    evaluator = AgentEvaluator()
    summary_results = []

    logger.info(
        f"🚀 开始执行批量 Agent 评测任务，共有 {len(TEST_DATASET)} 个 Benchmark 案例..."
    )

    for test_case in TEST_DATASET:
        logger.info(
            f"\n▶ Running Test Case: [{test_case['id']}] - {test_case['description']}"
        )

        # 1. 执行 Autonomous Repair Loop
        agent_result = agent.run_autonomous_fix_loop(
            initial_code=test_case["buggy_code"], test_code=test_case["test_code"]
        )

        # 2. 评测量化得分
        metrics = evaluator.evaluate_repair_job(
            agent_result=agent_result, max_allowed_steps=5
        )

        record = {
            "id": test_case["id"],
            "success": agent_result["success"],
            "iterations": agent_result["total_iterations"],
            "token_usage": agent_result["token_stats"],
            "metrics": metrics,
        }
        summary_results.append(record)

    # 3. 输出汇总报表
    logger.info(
        "\n======================== [EVALUATION SUMMARY REPORT] ========================"
    )
    print(json.dumps(summary_results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_batch_evaluation()
