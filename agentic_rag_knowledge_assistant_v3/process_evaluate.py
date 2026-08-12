import json
import os
import time

# 1. 严格复用你 config 中配置好的全局 logger
from config import logger

# 2. 引入你编译好的 LangGraph 图实例
from agent_workflow import app

# 文件路径配置
DATASET_PATH = "data/eval_dataset.json"
CHECKPOINT_PATH = "data/eval_results_checkpoint.json"


def load_dataset():
    if not os.path.exists(DATASET_PATH):
        logger.error(
            f"【评测中断】未找到评测数据集文件: {DATASET_PATH}，请先运行 download_data.py"
        )
        return []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取历史断点文件失败 ({e})，将重新开始评测。")
    return {}


def save_checkpoint(data):
    # 状态及时保存：每处理完一个 query 立即写入磁盘，防止 bug 崩溃导致大模型 token 浪费
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main_evaluation():
    logger.info(
        "================== 启动大模型 Agent 工业级 RAG 评测车间 =================="
    )

    dataset = load_dataset()
    if not dataset:
        return

    results_db = load_checkpoint()
    logger.info(
        f"评测配置加载成功。总数据量: {len(dataset)} 条 | 已完成断点进度: {len(results_db)} 条"
    )
    dataset = dataset[:5]
    for idx, item in enumerate(dataset):
        q_id = item["id"]
        query = item["query"]
        expected = item["expected_answer"]

        # 【核心要求3】断点续传检查：如果当前 ID 已经跑过，直接跳过
        if q_id in results_db:
            continue

        # 【核心要求2】重要节点 Logger 输出：可视化评测宏观进度
        logger.info(f"进度统计 -> [{idx+1}/{len(dataset)}] 正在评测数据项 ID: {q_id}")

        start_perf = time.time()

        try:
            # 执行 LangGraph 工作流
            # 输入符合你的 AgentState 结构的初始 query
            final_state = app.invoke({"query": query})

            # 【核心要求1】从 LangGraph 最终状态机字典中抽丝剥茧，提取完整的中间过程
            needs_retrieval = final_state.get("needs_retrieval", True)
            raw_documents = final_state.get(
                "raw_documents", []
            )  # retriever.invoke 召回的 Milvus+ES 去重混合块
            reranked_documents = final_state.get(
                "documents", []
            )  # Rerank 精选后的 3 块精华
            final_generation = final_state.get("generation", "")

            # 辅助状态评估指标
            retry_count = final_state.get("retry_count", 0)
            is_relevant = final_state.get("is_relevant", None)
            is_hallucination = final_state.get("is_hallucination", None)

            # 【核心要求2】重要核心执行流程节点进行详细日志可视化输出
            logger.info(
                f" └── [流程决策]: 意图分析 needs_retrieval = {needs_retrieval}"
            )
            if needs_retrieval:
                logger.info(
                    f" └── [检索召回]: 混合双路(Milvus+ES)共召回 {len(raw_documents)} 个文档块"
                )
                logger.info(
                    f" └── [重排过滤]: Reranker 精选保留了 {len(reranked_documents)} 个文档块"
                )
                logger.info(
                    f" └── [状态追踪]: 查询重写次数 = {retry_count} | 最终相关性评估 = {is_relevant} | 幻觉检测 = {is_hallucination}"
                )
            else:
                logger.info(
                    f" └── [直连生成]: 触发日常闲聊/通用常识通道，跳过知识库检索"
                )

            # 组装完整的中间链路数据结构
            results_db[q_id] = {
                "query": query,
                "expected_answer": expected,
                "intermediate_steps": {
                    "needs_retrieval": needs_retrieval,
                    "hybrid_recall_count": len(raw_documents),
                    "hybrid_recall_chunks": raw_documents,  # 存下向量+ES召回的文本
                    "reranker_chunks": reranked_documents,  # 存下 Rerank 后的文本
                    "retry_count": retry_count,
                    "is_relevant": is_relevant,
                    "is_hallucination": is_hallucination,
                },
                "final_answer": final_generation,
                "elapsed_seconds": round(time.time() - start_perf, 2),
            }

            # 【核心要求3】及时的状态保存，写在 try 的末尾，确保成功跑完这一条后立马稳健落盘
            save_checkpoint(results_db)
            logger.info(
                f" └── [持久化]: 数据项 {q_id} 中间状态及结果保存成功。本条耗时: {results_db[q_id]['elapsed_seconds']}s\n"
            )

        except Exception as e:
            # 捕获图运行中任意节点出现的 bug
            logger.error(
                f"【评测异常中断】在处理数据项 {q_id} 时发生致命错误: {str(e)}",
                exc_info=True,
            )
            logger.warning(
                "已经落盘的进度不会丢失。修复代码 Bug 后直接重新运行本脚本即可无缝续传。"
            )
            break

    if len(results_db) == len(dataset):
        logger.info(
            "================== 恭喜！所有真实业务数据评测任务圆满全量完成！ =================="
        )
        logger.info(f"包含完整中间流转痕迹的评测报告请查收: {CHECKPOINT_PATH}")


if __name__ == "__main__":
    main_evaluation()
