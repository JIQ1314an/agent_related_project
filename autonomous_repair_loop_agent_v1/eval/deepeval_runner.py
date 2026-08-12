import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False


class AgentDeepEvalSuite:
    @staticmethod
    def evaluate_task_completion(
        task_desc: str, agent_output: str, expected_behavior: str
    ):
        if not DEEPEVAL_AVAILABLE:
            print("[DeepEval] 未安装 deepeval 模块，跳过评估")
            return 0.0

        task_completion_metric = GEval(
            name="Task Completion",
            criteria="判断 Agent 生成的代码是否彻底解决了需求中的业务逻辑与边界约束。",
            evaluation_params=[
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
        )

        test_case = LLMTestCase(
            input=task_desc,
            actual_output=agent_output,
            expected_output=expected_behavior,
        )

        task_completion_metric.measure(test_case)
        return task_completion_metric.score
