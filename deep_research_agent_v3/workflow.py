import sqlite3
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver as SqliteSaver

from config import settings
from logger import logger
from models import State
from agents.planner import ResearchPlannerAgent
from agents.searcher import WebSearcherAgent
from agents.analyzer import DocumentAnalyzerAgent
from agents.writer import ReportWriterAgent
from agents.reviewer import QualityReviewerAgent

DB_PATH = "checkpoints.db"


class ResearchWorkflow:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.planner = ResearchPlannerAgent()
        self.searcher = WebSearcherAgent()
        self.analyzer = DocumentAnalyzerAgent()
        self.writer = ReportWriterAgent()
        self.reviewer = QualityReviewerAgent()

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(self.conn)
        self.graph = self._build_graph()

    def _planner_node(self, state: State) -> Dict[str, Any]:
        logger.info(
            f"========== [STATE ENGINE] [Task: {state.task_id}] 节点 1: Planner =========="
        )
        feedback = state.review.feedback if state.review else ""
        plan = self.planner.run(state.topic, task_id=state.task_id, feedback=feedback)
        return {"plan": plan}

    def _searcher_node(self, state: State) -> Dict[str, Any]:
        logger.info(
            f"========== [STATE ENGINE] [Task: {state.task_id}] 节点 2: Searcher =========="
        )
        search_results = self.searcher.run(state.plan, task_id=state.task_id)
        return {"search_results": search_results}

    def _analyzer_node(self, state: State) -> Dict[str, Any]:
        logger.info(
            f"========== [STATE ENGINE] [Task: {state.task_id}] 节点 3: Analyzer =========="
        )
        analyzed_docs = self.analyzer.run(state.search_results, task_id=state.task_id)
        return {"analyzed_docs": analyzed_docs}

    def _writer_node(self, state: State) -> Dict[str, Any]:
        current_iteration = state.iteration_count + 1
        logger.info(
            f"========== [STATE ENGINE] [Task: {state.task_id}] 节点 4: Writer (第 {current_iteration} 次) =========="
        )
        feedback = state.review.feedback if state.review else ""

        # 1. 精准从 state.plan 中提取 Planner 识别出来的课题类型
        category = (
            getattr(state.plan, "category", "general") if state.plan else "general"
        )

        # 2. 传入 category（保留原有的 topic, analyzed_docs, task_id, feedback 完整参数）
        report = self.writer.run(
            state.topic,
            state.analyzed_docs,
            task_id=state.task_id,
            feedback=feedback,
            category=category,  # <-- 新增传入分类
        )
        return {"report_draft": report, "iteration_count": current_iteration}

    def _reviewer_node(self, state: State) -> Dict[str, Any]:
        logger.info(
            f"========== [STATE ENGINE] [Task: {state.task_id}] 节点 5: Reviewer =========="
        )
        review = self.reviewer.run(
            state.topic, state.report_draft, task_id=state.task_id
        )

        if review.passed or state.iteration_count >= settings.MAX_REVISION_LOOPS:
            return {"review": review, "final_report": state.report_draft}
        else:
            return {"review": review}

    def _should_continue(self, state: State) -> str:
        if state.final_report:
            return "end"
        return "planner"

    def _build_graph(self):
        workflow = StateGraph(State)

        workflow.add_node("planner", self._planner_node)
        workflow.add_node("searcher", self._searcher_node)
        workflow.add_node("analyzer", self._analyzer_node)
        workflow.add_node("writer", self._writer_node)
        workflow.add_node("reviewer", self._reviewer_node)

        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "searcher")
        workflow.add_edge("searcher", "analyzer")
        workflow.add_edge("analyzer", "writer")
        workflow.add_edge("writer", "reviewer")

        workflow.add_conditional_edges(
            "reviewer", self._should_continue, {"end": END, "planner": "planner"}
        )

        return workflow.compile(checkpointer=self.checkpointer)

    def run(self, topic: str, thread_id: str, config: Optional[dict] = None) -> State:
        run_config = {"configurable": {"thread_id": thread_id}}
        if config:
            run_config.update(config)

        # 在全局状态初始化时写入 task_id
        initial_state = State(topic=topic, task_id=thread_id)
        logger.info(
            f"[Workflow] 启动新任务 | Task/Thread ID: [{thread_id}] | 课题: '{topic}'"
        )
        final_state = self.graph.invoke(initial_state, config=run_config)
        return final_state

    def resume(self, thread_id: str, config: Optional[dict] = None) -> State:
        run_config = {"configurable": {"thread_id": thread_id}}
        if config:
            run_config.update(config)

        snapshot = self.graph.get_state(run_config)
        if not snapshot or not snapshot.values:
            raise ValueError(f"未找到 Task ID '{thread_id}' 的断点记录。")

        logger.info(f"[Workflow] 读取 Task ID [{thread_id}] 快照并恢复运行...")
        final_state = self.graph.invoke(None, config=run_config)
        return final_state

    def get_task_status(self, thread_id: str) -> Optional[dict]:
        run_config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(run_config)
        if snapshot and snapshot.values:
            return {
                "values": snapshot.values,
                "next": snapshot.next,
            }
        return None
