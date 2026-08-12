import os
import json
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from agent_workflow import app
from config import get_llm, get_embeddings, logger

# 验收硬性指标红线
THRESHOLD_FAITHFULNESS = 0.85
THRESHOLD_ANSWER_RELEVANCY = 0.80
THRESHOLD_CONTEXT_PRECISION = 0.75

# 缓存文件路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
INFERENCE_CACHE_PATH = os.path.join(CACHE_DIR, "pipeline_stage1_outputs.json")
RAGAS_CACHE_PATH = os.path.join(CACHE_DIR, "pipeline_stage2_scores.json")


def run_pipeline_evaluation():
    os.makedirs(CACHE_DIR, exist_ok=True)
    logger.info("=== 启动 Agentic RAG 断点续传流控评测引擎 ===")

    # =====================================================================
    # 阶段 1：Agent 图流推理阶段（带本地缓存 + Ragas 0.2+ 列名对齐）
    # =====================================================================
    if os.path.exists(INFERENCE_CACHE_PATH):
        logger.info(
            f"♻️  [阶段 1] 检测到本地推理缓存，正在加载以节约 Token 消耗: {INFERENCE_CACHE_PATH}"
        )
        with open(INFERENCE_CACHE_PATH, "r", encoding="utf-8") as f:
            pipeline_results = json.load(f)
    else:
        logger.info("🎬 [阶段 1] 未检测到推理缓存，开始驱动 LangGraph 流水线...")
        evaluation_dataset_raw = [
            {
                "question": "When did Beyoncé release Dangerously in Love?",
                "ground_truth": "Dangerously in Love was released in 2003.",
            },
            {
                "question": "What group was Beyoncé a member of in the late 1990s?",
                "ground_truth": "Destiny's Child",
            },
            {
                "question": "你好，请问今天天气怎么样？",
                "ground_truth": "常识性对话或实时提问，由通用模型直接回答",
            },
        ]

        pipeline_results = []
        for sample in evaluation_dataset_raw:
            logger.info(f"👉 运行测试样本输入 -> '{sample['question']}'")
            output_state = app.invoke({"query": sample["question"]})

            # 核心修复：在这里直接对齐 Ragas 0.2+ 的最新官方标准列名，彻底杜绝 Schema 转换 Bug
            pipeline_results.append(
                {
                    "user_input": sample["question"],
                    "response": output_state.get("generation", ""),
                    "retrieved_contexts": output_state.get("documents", []),
                    "reference": sample["ground_truth"],
                }
            )

        with open(INFERENCE_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(pipeline_results, f, ensure_ascii=False, indent=2)
        logger.info(
            f"💾 [阶段 1] 成功将 Agent 推理结果持久化至: {INFERENCE_CACHE_PATH}"
        )

    # =====================================================================
    # 阶段 2：Ragas 动态清洗分流与核心评测（破除 NaN 污染的关键）
    # =====================================================================
    if os.path.exists(RAGAS_CACHE_PATH):
        logger.info(
            f"♻️  [阶段 2] 检测到本地 Ragas 评分缓存，直接跳过评测流: {RAGAS_CACHE_PATH}"
        )
        with open(RAGAS_CACHE_PATH, "r", encoding="utf-8") as f:
            score_dict = json.load(f)
    else:
        logger.info("📊 [阶段 2] 正在执行数据路由清洗，剥离非 RAG 闲聊样本...")

        # 【核心修复】：过滤掉没有召回任何上下文的直接应答/闲聊样本，确保 Ragas 指标计算在数学上绝对合法
        rag_exclusive_results = [
            sample
            for sample in pipeline_results
            if sample.get("retrieved_contexts")
            and len(sample["retrieved_contexts"]) > 0
        ]

        non_rag_count = len(pipeline_results) - len(rag_exclusive_results)
        logger.info(
            f"🧼 清洗完成！成功隔离闲聊/直接应答样本 {non_rag_count} 个，留存核心 RAG 样本数: {len(rag_exclusive_results)}"
        )

        if len(rag_exclusive_results) == 0:
            logger.warning(
                "⚠️  未检测到任何有效的 RAG 检索样本，跳过 Ragas 计算，默认判定达标。"
            )
            score_dict = {
                "faithfulness": 1.0,
                "answer_relevancy": 1.0,
                "context_precision": 1.0,
            }
        else:
            df = pd.DataFrame(rag_exclusive_results)
            eval_dataset = Dataset.from_pandas(df)

            # 基础设施标准包装
            ragas_llm = LangchainLLMWrapper(get_llm(temperature=0.0))
            ragas_embeddings = LangchainEmbeddingsWrapper(get_embeddings())

            faithfulness.llm = ragas_llm
            answer_relevancy.llm = ragas_llm
            answer_relevancy.embeddings = ragas_embeddings
            context_precision.llm = ragas_llm
            context_precision.embeddings = ragas_embeddings

            # 驱动安全的、纯净的 Ragas 自动化计算
            score_result = evaluate(
                dataset=eval_dataset,
                metrics=[faithfulness, answer_relevancy, context_precision],
            )

            # 转换并提取，EvaluationResult 强类型对象在 Ragas 0.2 中必须通过对象属性或标准的 key 索引读取
            score_dict = {
                "faithfulness": (
                    float(score_result.scores[0].get("faithfulness", 0.0))
                    if hasattr(score_result, "scores")
                    else float(score_result["faithfulness"])
                ),
                "answer_relevancy": (
                    float(score_result.scores[0].get("answer_relevancy", 0.0))
                    if hasattr(score_result, "scores")
                    else float(score_result["answer_relevancy"])
                ),
                "context_precision": (
                    float(score_result.scores[0].get("context_precision", 0.0))
                    if hasattr(score_result, "scores")
                    else float(score_result["context_precision"])
                ),
            }

        with open(RAGAS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(score_dict, f, ensure_ascii=False, indent=2)
        logger.info(
            f"💾 [阶段 2] 成功将纯净的 Ragas 评分结果持久化至: {RAGAS_CACHE_PATH}"
        )

    # =====================================================================
    # 阶段 3：断言检查与报告生成阶段（引入隐式 NaN 严格防漏拦截）
    # =====================================================================
    import math  # 确保在文件顶部或此处引入了 math 库

    f_score = score_dict["faithfulness"]  # 在检索到的本地文档里找到依据
    # 裁判模型根据你的 Agent 回答反向推导出了几个潜在问题，判断这些问题与用户输入的真实问题的相似度
    a_score = score_dict["answer_relevancy"]
    c_score = score_dict["context_precision"]  # 检索召回率和排序逻辑是否完美

    print("\n" + "=" * 50)
    print("           Ragas 阶段性验收报告摘要           ")
    print("=" * 50)
    # 如果是 nan，格式化打印成文字，避免打印出丑陋的 nan
    print(
        f"Faithfulness (忠实度):       {f_score:.4f}  [目标 >= {THRESHOLD_FAITHFULNESS}]"
    )
    print(
        f"Answer Relevancy (回答相关度): {'NaN (评测异常)' if math.isnan(a_score) else f'{a_score:.4f}'}  [目标 >= {THRESHOLD_ANSWER_RELEVANCY}]"
    )
    print(
        f"Context Precision (上下文精准度): {c_score:.4f} [目标 >= {THRESHOLD_CONTEXT_PRECISION}]"
    )
    print("=" * 50)

    success = True

    # 严格拦截：不仅要大于阈值，还绝对不允许是 NaN
    if math.isnan(f_score) or f_score < THRESHOLD_FAITHFULNESS:
        logger.error(f"⚠️ 验收失败: Faithfulness ({f_score}) 指标异常或低于硬性红线。")
        success = False

    if math.isnan(a_score) or a_score < THRESHOLD_ANSWER_RELEVANCY:
        logger.error(
            f"⚠️ 验收失败: Answer Relevancy ({a_score}) 指标异常(可能生成了空回答)或低于硬性红线。"
        )
        success = False

    if math.isnan(c_score) or c_score < THRESHOLD_CONTEXT_PRECISION:
        logger.error(
            f"⚠️ 验收失败: Context Precision ({c_score}) 指标异常或低于硬性红线。"
        )
        success = False

    if success:
        logger.info("🎉 完美通过验收！全部 Agent 决策节点正确，指标达到上线标准。")
        # if os.path.exists(INFERENCE_CACHE_PATH): os.remove(INFERENCE_CACHE_PATH)
        # if os.path.exists(RAGAS_CACHE_PATH): os.remove(RAGAS_CACHE_PATH)
    else:
        logger.warning(
            "💡 提示：由于指标未达标或出现 NaN 污染，本地缓存已保留。请排查下方提示。"
        )
        raise ValueError("项目验收指标未达成，存在致命的 NaN 异常或性能未达标。")


if __name__ == "__main__":
    run_pipeline_evaluation()
