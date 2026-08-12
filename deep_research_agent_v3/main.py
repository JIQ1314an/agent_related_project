import os
import sys
import uuid
from logger import logger
from workflow import ResearchWorkflow
from observer import init_langfuse_callback

RESEARCH_TOPICS = [
    "2026年AI Agent框架发展趋势与选型",
    "MCP协议在企业级AI应用中的落地实践",
    "Agentic RAG相比传统RAG的优势与局限",
    "多Agent协作系统的架构设计与生产部署",
    "LLM幻觉问题的检测与缓解策略",
    "Context Engineering vs Prompt Engineering实战对比",
    "Harness Engineering在Agent生产化中的应用",
    "Loop Engineering与自主循环Agent的未来",
    "Hermes/OpenClaw/OpenCode三大Agent框架对比",
    "AI Agent评测体系：从Benchmark到生产评测",
]


def print_menu():
    print("\n==================================================")
    print("      Deep Research Agent (CLI 工业级控制台)       ")
    print("==================================================")
    print(" [1] 发起全新研究任务")
    print(" [2] 🔄 恢复上一次打断的任务 (断点续传)")
    print("==================================================")


def print_topics():
    print("\n---------------- 预置研究课题 ----------------")
    for idx, topic in enumerate(RESEARCH_TOPICS, 1):
        print(f" [{idx}] {topic}")
    print(" [0] 输入自定义研究课题")
    print("----------------------------------------------")


def main():
    print_menu()
    mode = input("请选择运行模式 (1 或 2): ").strip()

    workflow = ResearchWorkflow()
    langfuse_cb = init_langfuse_callback()
    config = {"callbacks": [langfuse_cb]} if langfuse_cb else None

    # ---------------- 模式 1：发起全新任务 ----------------
    if mode != "2":
        print_topics()
        try:
            choice = input("请选择要研究的课题编号 (0-10): ").strip()
            if choice == "0":
                topic = input("请输入自定义研究课题: ").strip()
                if not topic:
                    print("输入为空，默认选择课题 1")
                    topic = RESEARCH_TOPICS[0]
            else:
                idx = int(choice) - 1
                topic = (
                    RESEARCH_TOPICS[idx]
                    if 0 <= idx < len(RESEARCH_TOPICS)
                    else RESEARCH_TOPICS[0]
                )
        except Exception as e:
            logger.error(f"输入解析失败，使用默认课题 1: {e}")
            topic = RESEARCH_TOPICS[0]

        # 核心修改 1: 为命令行任务自动生成唯一的 thread_id
        thread_id = f"cli-{uuid.uuid4().hex[:8]}"
        logger.info(
            f"成功创建任务 | Thread ID (断点凭证): [{thread_id}] | 目标课题: '{topic}'"
        )

        try:
            # 核心修改 2: 调用 run 时传入 thread_id
            result_state = workflow.run(topic=topic, thread_id=thread_id, config=config)
            final_report = result_state.get("final_report") or result_state.get(
                "report_draft", ""
            )
        except Exception as e:
            logger.error(f"\n❌ 任务执行中断: {str(e)}")
            logger.warning(
                f"💡 断点已自动存入数据库！下次运行 main.py 选择模式 [2]，并输入 Thread ID: [{thread_id}] 即可恢复。"
            )
            sys.exit(1)

    # ---------------- 模式 2：断点续传 ----------------
    else:
        resume_thread_id = input(
            "\n请输入上次中断的任务 Thread ID (例如 cli-a1b2c3d4): "
        ).strip()
        if not resume_thread_id:
            logger.error("未输入 Thread ID，程序退出。")
            sys.exit(1)

        try:
            # 核心修改 3: 调用 workflow.resume(...) 读取数据库快照接着跑
            logger.info(f"正在从 SQLite 数据库提取 [{resume_thread_id}] 的历史快照...")
            result_state = workflow.resume(thread_id=resume_thread_id, config=config)
            final_report = result_state.get("final_report") or result_state.get(
                "report_draft", ""
            )
            topic = result_state.get("topic", "Resumed_Task")
        except Exception as e:
            logger.error(f"恢复失败: {str(e)}")
            sys.exit(1)

    # 保存文件输出
    output_filename = f"Research_Report_{topic[:15].replace(' ', '_')}.md"
    output_dir_path = os.path.join(os.getcwd(), "output")
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path)

    output_path = os.path.join(output_dir_path, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_report)

    logger.info("==================================================")
    logger.info(" [完成] 执行成功！")
    logger.info(f" 最终研究报告已生成至: {output_path}")
    logger.info(f" 报告字符数统计: {len(final_report)} 字符")
    logger.info("==================================================")


if __name__ == "__main__":
    main()
