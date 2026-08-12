import streamlit as st
import uuid
import time
from workflow import ResearchWorkflow
from observer import init_langfuse_callback
from logger import logger

st.set_page_config(
    page_title="Deep Research Agent 控制台", page_icon="🔬", layout="wide"
)

# 1. 初始化全局 session_state，防止页面刷新 (Rerun) 导致生成的报告内容丢失
if "final_report" not in st.session_state:
    st.session_state.final_report = None
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None

# CSS 样式优化
st.markdown(
    """
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #0F172A; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1rem; color: #475569; margin-bottom: 1.5rem; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-title">🔬 Deep Research Agent 工业级控制台</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-title">基于 LangGraph State Machine + SQLite Checkpointer 的深度研究生成系统</div>',
    unsafe_allow_html=True,
)


@st.cache_resource
def get_workflow():
    return ResearchWorkflow()


workflow = get_workflow()

# 侧边栏模式选择
st.sidebar.header("⚙️ 任务模式设置")
mode = st.sidebar.radio("选择操作模式", ["新建研究任务", "🔄 断点续传 / 恢复任务"])

PRESET_TOPICS = [
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

if mode == "新建研究任务":
    st.subheader("📝 发起全新深度研究")

    col1, col2 = st.columns([3, 2])
    with col1:
        topic_type = st.radio(
            "课题来源", ["预置 10 大核心课题", "自定义课题"], horizontal=True
        )
        if topic_type == "预置 10 大核心课题":
            selected_topic = st.selectbox("选择课题", PRESET_TOPICS)
        else:
            selected_topic = st.text_input(
                "输入自定义课题",
                placeholder="例如：大模型 Agent 在医疗领域的落地架构分析",
            )

    with col2:
        default_thread_id = f"task-{uuid.uuid4().hex[:8]}"
        thread_id = st.text_input(
            "任务 Thread ID (持久化追踪凭证)", value=default_thread_id
        )

    st.divider()

    if st.button("🚀 开始深度研究任务", type="primary", use_container_width=True):
        if not selected_topic.strip():
            st.error("请输入有效的研究课题！")
        else:
            langfuse_cb = init_langfuse_callback()
            config = {"callbacks": [langfuse_cb]} if langfuse_cb else None

            status_box = st.empty()
            status_box.info(f"⏳ 正在启动工作流... Thread ID: `{thread_id}`")

            try:
                start_time = time.time()
                result_state = workflow.run(
                    topic=selected_topic, thread_id=thread_id, config=config
                )
                elapsed = time.time() - start_time

                status_box.success(f"🎉 任务顺利完成！总耗时: {elapsed:.1f} 秒")

                # 核心修复：把生成结果存入 session_state
                st.session_state.final_report = result_state.get(
                    "final_report"
                ) or result_state.get("report_draft", "")
                st.session_state.current_thread_id = thread_id

            except Exception as e:
                logger.error(f"任务中断报错: {str(e)}", exc_info=True)
                status_box.error(f"❌ 运行异常终止: {str(e)}")
                st.warning(
                    f"💡 **断点已安全保存！**\n\n"
                    f"当前进度已锁定在数据库中。请复制凭证 **`{thread_id}`**，在侧边栏切换至【断点续传】模式即可恢复！"
                )

elif mode == "🔄 断点续传 / 恢复任务":
    st.subheader("🔄 从中断现场恢复运行")
    st.info(
        "原理：网络中断或大模型限流挂掉时，SQLite 数据库已将成功的节点写入磁盘。输入 Thread ID 即可直接恢复未完成的工作。"
    )

    resume_thread_id = st.text_input(
        "输入需要恢复的任务 Thread ID", placeholder="例如：task-a1b2c3d4"
    )

    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        if st.button("🔍 查询快照状态", use_container_width=True):
            if resume_thread_id:
                status_info = workflow.get_task_status(resume_thread_id)
                if status_info:
                    st.success("成功匹配到数据库快照！")

                    # 定义标准的按顺序节点流水线
                    NODE_PIPELINE = [
                        ("planner", "Planner (计划生成)"),
                        ("searcher", "Searcher (全网检索)"),
                        ("analyzer", "Analyzer (文档分析)"),
                        ("writer", "Writer (报告初稿)"),
                        ("reviewer", "Quality Reviewer (质量审核)"),
                    ]

                    next_node_tuple = status_info.get("next")
                    # LangGraph 的 next 通常是元组形式，如 ('writer',)
                    next_node_name = (
                        next_node_tuple[0]
                        if (next_node_tuple and len(next_node_tuple) > 0)
                        else None
                    )

                    # 核心修复：根据真实的 next 节点，精准切片推算此前已经真正完成的节点
                    completed_labels = []
                    if next_node_name:
                        for node_id, node_label in NODE_PIPELINE:
                            if node_id == next_node_name:
                                break
                            completed_labels.append(node_label)
                    else:
                        # 如果 next 为空，说明整套流程已经全部执行完毕
                        completed_labels = [label for _, label in NODE_PIPELINE]

                    if completed_labels:
                        st.markdown(
                            f"**已成功完成的节点:** { ' ➡️ '.join(completed_labels) }"
                        )
                    else:
                        st.markdown("**已成功完成的节点:** (尚未开始执行)")

                    if next_node_name:
                        node_dict = dict(NODE_PIPELINE)
                        next_label = node_dict.get(next_node_name, next_node_name)
                        st.markdown(
                            f"**断点位置 (接下来将从该节点恢复):** `{next_label}`"
                        )
                    else:
                        st.info(
                            "提示: 该 Thread ID 的所有节点已经完全执行完毕，无需恢复。"
                        )
                else:
                    st.error(
                        f"未找到 Thread ID `{resume_thread_id}` 的快照，请检查是否输入有误。"
                    )

    with col_btn2:
        if st.button("▶️ 恢复并继续运行", type="primary", use_container_width=True):
            if not resume_thread_id.strip():
                st.error("请输入有效的 Thread ID！")
            else:
                langfuse_cb = init_langfuse_callback()
                config = {"callbacks": [langfuse_cb]} if langfuse_cb else None

                status_box = st.empty()
                status_box.info(
                    f"⏳ 正在加载快照 `{resume_thread_id}`，准备接续运行未完成节点..."
                )

                try:
                    start_time = time.time()
                    result_state = workflow.resume(
                        thread_id=resume_thread_id, config=config
                    )
                    elapsed = time.time() - start_time

                    status_box.success(
                        f"🎉 成功恢复并补全剩余所有节点！耗时: {elapsed:.1f} 秒"
                    )

                    # 核心修复：把恢复生成的结果存入 session_state
                    st.session_state.final_report = result_state.get(
                        "final_report"
                    ) or result_state.get("report_draft", "")
                    st.session_state.current_thread_id = resume_thread_id

                except Exception as e:
                    logger.error(f"断点恢复失败: {str(e)}", exc_info=True)
                    status_box.error(f"❌ 恢复失败: {str(e)}")

# ---------------- 2. 统一全屏渲染成果展示区 ----------------
# 脱离按钮与两列网格的约束，独立在最外层渲染，保证 100% 全屏宽度且在下载时不丢失
if st.session_state.final_report:
    st.divider()
    st.markdown("### 📄 生成的研究报告成果")

    # 渲染 Markdown 格式内容（自动占满 100% 页面宽度）
    st.markdown(st.session_state.final_report)

    # 下载按钮（点击触发页面刷新后，由于有 session_state 保持，报告依然稳定存在）
    st.download_button(
        label="📥 下载 Markdown 格式报告",
        data=st.session_state.final_report,
        file_name=f"{st.session_state.current_thread_id or 'Research'}_Report.md",
        mime="text/markdown",
    )
