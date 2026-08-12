from typing import List
from tavily import TavilyClient
from config import settings
from logger import logger
from models import SearchResultItem


class TavilySearchTool:
    """生产级 Tavily 搜索引擎封装，带 task_id 日志标记与长文本剪枝"""

    def __init__(self):
        if not settings.TAVILY_API_KEY:
            logger.error("[SearchTool] 致命错误: 未在环境中检测到 TAVILY_API_KEY")
            raise ValueError("TAVILY_API_KEY missing.")
        self.client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    def search(
        self, query: str, task_id: str = "SYS", max_results: int = 3
    ) -> List[SearchResultItem]:
        logger.info(f"[Task: {task_id}] [TavilySearch] 发起网页检索: '{query}'")
        try:
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=False,
                include_raw_content=False,
            )
            results = []
            for item in response.get("results", []):
                # 上下文控水：单条 content 截断至前 400 字符，防止冲爆 LLM Context
                content_snippet = item.get("content", "")[:400] + "..."
                results.append(
                    SearchResultItem(
                        title=item.get("title", "网页数据"),
                        url=item.get("url", ""),
                        content=content_snippet,
                        score=item.get("score", 0.0),
                        source_type="web",
                    )
                )
            logger.info(
                f"[Task: {task_id}] [TavilySearch] 获取到 {len(results)} 条网页结果。"
            )
            return results
        except Exception as e:
            logger.error(f"[Task: {task_id}] [TavilySearch] 异常: {str(e)}")
            return []
