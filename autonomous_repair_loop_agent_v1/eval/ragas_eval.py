import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from datasets import Dataset
    from pandas import DataFrame
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevance

    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False


class AgentRagasEvaluator:
    @staticmethod
    def run_ragas_assessment(questions: list, answers: list, contexts: list):
        if not RAGAS_AVAILABLE:
            print("[Ragas] 未安装 ragas 依赖，跳过评估")
            return None

        data = {"question": questions, "answer": answers, "contexts": contexts}
        df = DataFrame(data)
        dataset = Dataset.from_pandas(df)

        return evaluate(dataset=dataset, metrics=[faithfulness, answer_relevance])
