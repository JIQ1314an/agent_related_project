from typing import Dict, Any, List
from logger import logger


class AgentEvaluator:
    """
    针对 Agent Loop 性能与 quality 的量化评估器
    包含 2026 核心评估指标: Task Completion, Step Efficiency, Tool Correctness
    """

    def evaluate_repair_job(
        self, agent_result: Dict[str, Any], max_allowed_steps: int
    ) -> Dict[str, float]:
        """
        对单次 Loop 任务指标进行量化打分
        """
        success = agent_result["success"]
        steps_taken = agent_result["total_iterations"]

        # 1. Task Completion Rate (任务完成率): 0.0 或 1.0
        task_completion = 1.0 if success else 0.0

        # 2. Step Efficiency (步骤效率分): $1 - \frac{\text{steps\_taken} - 1}{\text{max\_allowed\_steps}}$
        if success:
            step_efficiency = max(0.0, 1.0 - ((steps_taken - 1) / max_allowed_steps))
        else:
            step_efficiency = 0.0

        # 3. Tool Correctness (沙箱/测试工具正确运用率)
        # 通过成功测试运行比例计算
        history = agent_result.get("history", [])
        successful_executions = sum(
            1
            for h in history
            if h.get("execution_time", 0) > 0 and h.get("exit_code") != -2
        )
        tool_correctness = successful_executions / len(history) if history else 0.0

        metrics = {
            "task_completion": task_completion,
            "step_efficiency": round(step_efficiency, 2),
            "tool_correctness": round(tool_correctness, 2),
            "overall_score": round(
                (
                    task_completion * 0.6
                    + step_efficiency * 0.2
                    + tool_correctness * 0.2
                ),
                2,
            ),
        }

        logger.info(f"[EVALUATION METRICS COMPUTED]: {metrics}")
        return metrics

    def run_ragas_eval(
        self, ground_truth_answer: str, generated_code: str
    ) -> Dict[str, Any]:
        """
        集成 Ragas 库评测代码在 Faithfulness/Answer Relevancy 上的表现
        """
        try:
            # 引入 Ragas 指标引擎
            from ragas import evaluate
            from ragas.metrics import faithfulness, answer_relevancy
            from datasets import Dataset

            data = {
                "question": [
                    "Fix the bug in python code according to unit test failures."
                ],
                "answer": [generated_code],
                "ground_truth": [ground_truth_answer],
            }
            dataset = Dataset.from_dict(data)

            # 评估得分
            results = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
            logger.info(f"[RAGAS EVAL SUCCESS]: {results}")
            return dict(results)

        except Exception as e:
            logger.warning(
                f"[RAGAS EVAL SKIPPED / FAILED]: Ragas 库依赖未完整就绪 ({str(e)})"
            )
            return {"faithfulness": 0.0, "answer_relevancy": 0.0}
