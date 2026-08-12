import json
import os
from datasets import load_dataset

# 直接复用你 config 里的全局 logger
from config import logger, HF_TOKEN


def build_clean_markdown_kb(
    data_dir="./data", num_eval_samples=40, kb_expansion_samples=250
):
    """
    下载真实中文长文本数据集，严格去重，并生成供知识库切块使用的标准 .md 文件。
    """
    logger.info("--- 📥 开始下载真实中文长文本数据集 (hfl/cmrc2018) ---")
    try:
        dataset = load_dataset("hfl/cmrc2018", split="train", token=HF_TOKEN)
    except Exception as e:
        logger.error(f"数据集下载失败，请检查网络或 HuggingFace 连接。错误: {e}")
        return

    os.makedirs(data_dir, exist_ok=True)

    unique_contexts = []
    seen_contexts = set()
    eval_qa_pairs = []

    logger.info("开始提取数据：正在对长文本进行严格去重，并筛选评测集...")

    # 扫描较大范围的数据，以确保能过滤出足够数量的独立不重复文章
    for idx, item in enumerate(
        dataset.select(range(min(kb_expansion_samples, len(dataset))))
    ):
        context = item.get("context", "").strip()
        question = item.get("question", "").strip()

        answers_dict = item.get("answers", {})
        answers_list = (
            answers_dict.get("text", []) if isinstance(answers_dict, dict) else []
        )
        expected_answer = answers_list[0] if answers_list else ""

        if not context or not question:
            continue

        # 【核心去重】如果这个长文本段落之前没遇见过，才放入知识库列表
        if context not in seen_contexts:
            seen_contexts.add(context)
            unique_contexts.append(context)

        # 控制评测问题集的大小，避免本地 CPU 跑 Embedding 慢死
        if len(eval_qa_pairs) < num_eval_samples:
            eval_qa_pairs.append(
                {
                    "id": f"cmrc_eval_{len(eval_qa_pairs):04d}",
                    "query": question,
                    "expected_answer": expected_answer,
                }
            )

    # 1. 独立输出为干净的标准 .md 文件，完美契合你的 DirectoryLoader 扫描
    logger.info(f"正在将去重后的 {len(unique_contexts)} 篇长文写入本地 .md 文件...")
    for c_idx, context_text in enumerate(unique_contexts):
        md_filename = f"industrial_doc_{c_idx+1:03d}.md"
        md_path = os.path.join(data_dir, md_filename)

        # 组装标准 markdown 格式
        md_content = f"# 商业与百科参考合规档案_{c_idx+1:03d}\n\n{context_text}\n"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    # 2. 保存配套的不重复评测集
    qa_eval_path = os.path.join(data_dir, "eval_dataset.json")
    with open(qa_eval_path, "w", encoding="utf-8") as f:
        json.dump(eval_qa_pairs, f, ensure_ascii=False, indent=2)

    logger.info("--- 🎉 工业级 RAG 评测数据源【去重版】构建完毕 ---")
    logger.info(
        f"1. 知识库：已生成 {len(unique_contexts)} 篇『绝对不重复』的独立 .md 文件，存放于 '{data_dir}/'"
    )
    logger.info(
        f"2. 评测集：已生成 {len(eval_qa_pairs)} 条高质量真实业务问答，保存至 '{qa_eval_path}'"
    )


if __name__ == "__main__":
    # 默认抽取40条做评测（CPU速度快），扫描250条原始数据来为知识库提供丰富的不重复.md文档
    build_clean_markdown_kb(
        data_dir="./data", num_eval_samples=40, kb_expansion_samples=250
    )
