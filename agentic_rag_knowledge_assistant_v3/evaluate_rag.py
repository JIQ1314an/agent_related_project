import json
import os
import re
import sys

# 动态引入你的项目配置与大模型工厂函数
try:
    from config import get_llm

    # 🛡️ 修复 1：使用指定的裁判大模型，且固定 temperature=0.0 确保评分结果客观、可复现
    judge_llm = get_llm(model_name="qwen3.6-max-preview", temperature=0.0)
except ImportError:
    print(
        "❌ 错误: 无法从 config.py 导入 get_llm。请确保此评测脚本放置在项目根目录下！"
    )
    sys.exit(1)


def load_json_file(filepath):
    """安全读取JSON文件"""
    if not os.path.exists(filepath):
        print(f"❌ 错误：未找到必要文件 -> {filepath}")
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def llm_judge_score_via_langchain(query: str, expected: str, actual: str) -> float:
    """
    基于 LangChain ChatOpenAI 对象的 LLM-as-a-Judge 智能判分引擎
    """
    if not actual or str(actual).strip() == "" or str(actual).strip() == "None":
        return 0.0

    prompt_content = f"""你是一位极其严格的企业级 RAG 系统评测专家。
请对比【标准答案】与【系统回答】，评估系统的回答是否真正正确地解答了【用户问题】。

[评测上下文]
用户问题：{query}
标准答案：{expected}
系统实际回答：{actual}

[评分硬性基准]
1. 完全正确且涵盖所有核心要点：给 100 分。
2. 答出了核心要点，但遗漏了部分非关键数字或存在极细微瑕疵：给 70-90 分。
3. 答非所问、逻辑严重自相矛盾、或者出现严重幻觉：给 0 分。
4. 如果标准答案本身提示这是“日常闲聊”或“通用常识”，只要系统的实际回答符合常理且没有胡说八道，即可给 95-100 分。

请完全基于事实一致性进行打分。除了输出一个 0 到 100 之间的纯整数数字外，绝对不要附加任何解释、任何前缀或标点符号！"""

    try:
        from langchain_core.messages import HumanMessage

        response = judge_llm.invoke([HumanMessage(content=prompt_content)])

        score_text = str(response.content).strip()
        match = re.search(r"\d+", score_text)
        if match:
            return float(match.group())
        return 0.0
    except Exception as e:
        print(f"  ⚠️ 裁判模型调用异常: {e}，自动降级为基础关键词覆盖率兜底评分。")
        hit_count = sum(
            1
            for word in [
                "部分",
                "满分",
                "居委会",
                "政府",
                "操作证",
                "停止",
                "温度",
                "安全",
                "流量",
                "幻觉",
            ]
            if word in expected and word in str(actual)
        )
        return 50.0 if hit_count > 0 else 0.0


def check_required_entities(chunks, required_entities):
    """
    轻量级实体覆盖率检查：
    如果 required_entities 为空，则视为 Pass（无需检索）；
    否则，必须全部命中才视为 Pass。
    """
    if not required_entities:
        return True, []

    # 将 chunks 拍平，快速检索
    full_text = " ".join([str(c) for c in chunks]).lower()

    missing = [ent for ent in required_entities if ent.lower() not in full_text]
    return len(missing) == 0, missing


def main():
    # 🛡️ 修复 2：将 checkpoint 的路径切换到指定的 ./data 目录下
    data_dir = "./data"
    dataset_path = os.path.join(data_dir, "eval_dataset.json")
    checkpoint_path = os.path.join(data_dir, "eval_results_checkpoint.json")

    print("=" * 80)
    print("🎯 正在启动 RAG 双维能力全自动化深度评测流水线...")
    print("=" * 80)

    # 读取标准数据集与运行检查点
    gt_dataset = load_json_file(dataset_path)
    rag_results = load_json_file(checkpoint_path)

    if not gt_dataset or not rag_results:
        print("❌ 核心数据缺失，评测强行终止。")
        return

    # 将大字典结构的 RAG 结果转换为标准对齐字典映射
    results_map = {}
    if isinstance(rag_results, dict):
        for k, v in rag_results.items():
            if isinstance(v, dict):
                # 优先匹配内容里自带的 id，其次使用大字典的外层 Key 作为 Case_ID
                cid = v.get("id") or v.get("case_id") or k
                results_map[cid] = v

    # 考纲硬性目标矩阵（精确挂钩你的 test_purpose 逻辑）
    gold_rules = {
        "test_case_01_vector": {
            "need_retrieval": True,
            "target_doc": "doc_001_ijso.md",
        },
        "test_case_02_es": {
            "need_retrieval": True,
            "target_doc": "doc_002_shanghai.md",
        },
        "test_case_03_hybrid_rerank": {
            "need_retrieval": True,
            "target_doc": "doc_003_industrial_safety.md",
        },
        "test_case_04_direct_chat": {"need_retrieval": False, "target_doc": None},
        "test_case_05_general_knowledge": {"need_retrieval": False, "target_doc": None},
    }

    report_details = []
    routing_success = 0
    retrieval_hits = 0
    generation_scores = []
    retrieval_needed_count = 0

    # 核心评测循环
    for case in gt_dataset:
        if not isinstance(case, dict):
            continue

        case_id = case.get("id")
        query = case.get("query", "")
        expected_ans = case.get("expected_answer", "")
        purpose = case.get("test_purpose", "")
        rule = gold_rules.get(case_id, {"need_retrieval": False, "target_doc": None})

        print(f"\n🎬 [🔍 正在评估用例] -> {case_id}")

        if case_id not in results_map:
            print(
                f"  ⚠️ 警告：在检查点文件中未检索到该 ID [{case_id}] 的执行结果，自动跳过。"
            )
            continue

        actual_run = results_map[case_id]

        # 🛡️ 修复 3：深入 intermediate_steps 嵌套字典解析数据
        inter_steps = actual_run.get("intermediate_steps", {})
        if not isinstance(inter_steps, dict):
            inter_steps = {}

        actual_routing = inter_steps.get("needs_retrieval", False)
        # 🛡️ 修复 4：将检索片段的提取目标锁定为你实际落盘的 "reranker_chunks"
        actual_chunks = inter_steps.get("reranker_chunks", [])
        actual_ans = actual_run.get("final_answer", "")

        # ==================== 维度一：更具防御性的路由比对 ====================
        # 强行支持 bool, 字符串 "true"/"false" 等各种奇葩落盘格式
        normalized_actual_routing = str(actual_routing).strip().lower()
        actual_routing_bool = normalized_actual_routing in ["true", "1", "yes"]

        is_routing_ok = actual_routing_bool == rule["need_retrieval"]
        if is_routing_ok:
            routing_success += 1
            routing_status = "✅ 路由正确"
        else:
            routing_status = "❌ 路由错误"

        # =====================================================================
        # 维度二：更具鲁棒性的通用召回命中判定
        # =====================================================================
        entities = case.get("required_entities", [])
        actual_chunks = inter_steps.get("reranker_chunks", [])

        is_hit, missing_list = check_required_entities(actual_chunks, entities)

        if is_hit:
            retrieval_hits += 1
            retrieval_status = "✅ 实体证据全覆盖"
        else:
            retrieval_status = f"❌ 丢失关键实体: {missing_list}"

        # 调试
        # print(
        #     f"  ├─ 🧭 意图路由: {routing_status} (预期: {rule['need_retrieval']}, 实际: {actual_routing})"
        # )
        # print(f"  ├─ 📥 检索召回: {retrieval_status}")
        # continue

        # 维度三：评测最终生成的质量得分
        print(f"  🤖 正在调用大模型裁判进行语义拟合评分...")
        score = llm_judge_score_via_langchain(query, expected_ans, actual_ans)
        generation_scores.append(score)

        print(
            f"  ├─ 🧭 意图路由: {routing_status} (预期: {rule['need_retrieval']}, 实际: {actual_routing})"
        )
        print(f"  ├─ 📥 检索召回: {retrieval_status}")
        print(f"  └─ 💯 裁判评分: {score} 分")

        report_details.append(
            {
                "id": case_id,
                "query": query,
                "test_purpose": purpose,
                "routing_ok": is_routing_ok,
                "retrieval_status": retrieval_status,
                "generation_score": score,
            }
        )

    # 汇总结算
    total_evaluated = len(generation_scores)
    if total_evaluated == 0:
        print(
            "❌ 错误：未成功评估任何对齐后的测试数据，请检查 checkpoint 的 ID 是否与 dataset 一致。"
        )
        return

    routing_acc = (routing_success / total_evaluated) * 100
    retrieval_hit_rate = (
        (retrieval_hits / retrieval_needed_count * 100)
        if retrieval_needed_count > 0
        else 100.0
    )
    avg_gen_score = sum(generation_scores) / total_evaluated

    print("\n" + "=" * 80)
    print("📊 🏆 最终 RAG 性能评测多维深度看板 🏆")
    print("=" * 80)
    print(
        f"  🎯 【意图分流准确率 (Router Acc)】 : {routing_acc:.2f}%  ({routing_success}/{total_evaluated})"
    )
    print(
        f"  🔍 【高噪检索命中率 (Recall Hit)】 : {retrieval_hit_rate:.2f}%  ({retrieval_hits}/{retrieval_needed_count})"
    )
    print(f"  📝 【大模型生成均分 (LLM Score)】  : {avg_gen_score:.2f} / 100 分")
    print("-" * 80)
    print("💾 数据保存中...")

    # 落盘为最终的评估报告
    report_output_path = os.path.join(data_dir, "final_eval_report.json")
    with open(report_output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metrics": {
                    "routing_accuracy": f"{routing_acc:.2f}%",
                    "retrieval_hit_rate": f"{retrieval_hit_rate:.2f}%",
                    "avg_generation_score": f"{avg_gen_score:.2f}",
                },
                "details": report_details,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"💾 核心评测报告已成功落盘至: {report_output_path}\n")


if __name__ == "__main__":
    main()
