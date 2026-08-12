from typing import Dict, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config import settings
from logger import logger
from models import SearchResultItem, AnalyzedDoc


class DocumentAnalyzerAgent:
    """[Agent 3] Document Analyzer"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            # openai_api_key=settings.OPENAI_API_KEY,
            # openai_api_base=settings.OPENAI_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            temperature=0.1,
        )

    def run(
        self, search_results: Dict[str, List[SearchResultItem]], task_id: str = "SYS"
    ) -> List[AnalyzedDoc]:
        logger.info(f"[Task: {task_id}] [AnalyzerAgent] 开始解析文档并提炼论点...")
        analyzed_docs = []

        for sub_title, items in search_results.items():
            logger.info(
                f"[Task: {task_id}] [AnalyzerAgent] 分析子课题 '{sub_title}' 的 {len(items)} 份多源文档..."
            )
            context_str = ""
            citations = []

            for idx, item in enumerate(items, 1):
                context_str += f"数据源 [{idx}] [{item.source_type.upper()}]: {item.title}\nURL: {item.url}\n摘要: {item.content}\n\n"
                citations.append({"title": item.title, "url": item.url})

            messages = [
                SystemMessage(
                    content="你是一名顶级技术文档分析师。请从给定的搜索摘要中抽取技术细节、架构逻辑与权威结论。"
                ),
                HumanMessage(
                    content=f"子课题名称: {sub_title}\n\n搜索数据:\n{context_str}\n\n请提取 4 到 6 条核心观点:"
                ),
            ]

            response = self.llm.invoke(messages)
            print(
                f"=== Analyzer ===\nmessage: 【{messages}】\n\n response: 【{response}】"
            )
            insights = [
                line.strip("- ")
                for line in response.content.split("\n")
                if line.strip()
            ]

            analyzed_docs.append(
                AnalyzedDoc(
                    sub_task_title=sub_title, key_insights=insights, citations=citations
                )
            )

        logger.info(
            f"[Task: {task_id}] [AnalyzerAgent] 提炼完成，生成 {len(analyzed_docs)} 组结构化情报。"
        )
        return analyzed_docs
