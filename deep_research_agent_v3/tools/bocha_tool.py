import requests
from typing import List
from config import settings
from logger import logger
from models import SearchResultItem


class BochaSearchTool:
    """国内博查 AI 搜索 API 封装，专门针对微信公众号、知乎、中文技术社区与新闻"""

    BASE_URL = "https://api.bochaai.com/v1/web-search"

    def __init__(self):
        # 建议在 .env 或 settings 中配置 BOCHA_API_KEY
        self.api_key = getattr(settings, "BOCHA_API_KEY", "")

    def search(
        self, query: str, task_id: str = "SYS", max_results: int = 3
    ) -> List[SearchResultItem]:
        if not self.api_key:
            logger.warning(
                f"[Task: {task_id}] [BochaSearch] 未配置 BOCHA_API_KEY，自动跳过国内博查检索。"
            )
            return []

        logger.info(f"[Task: {task_id}] [BochaSearch] 发起国内深度中文检索: '{query}'")
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "query": query,
                "freshness": "noLimit",
                "summary": True,
                "count": max_results,
            }

            response = requests.post(
                self.BASE_URL, json=payload, headers=headers, timeout=10
            )
            if response.status_code != 200:
                logger.error(
                    f"[Task: {task_id}] [BochaSearch] 请求失败，状态码: {response.status_code}, 响应: {response.text}"
                )
                return []

            data = response.json()
            results = []

            # 解析博查返回的 Web 页卡
            web_pages = data.get("data", {}).get("webPages", {}).get("value", [])
            for item in web_pages:
                title = item.get("name", "中文网页")
                url = item.get("url", "")
                snippet = item.get("snippet", "") or item.get("summary", "")

                # 控水：截断前 400 字符
                content_snippet = f"[国内社区/公众号数据]: {snippet[:400]}..."

                results.append(
                    SearchResultItem(
                        title=f"[中文] {title}",
                        url=url,
                        content=content_snippet,
                        score=0.9,
                        source_type="bocha",
                    )
                )

            logger.info(
                f"[Task: {task_id}] [BochaSearch] 获取到 {len(results)} 条高质量中文数据。"
            )
            return results
        except Exception as e:
            logger.error(f"[Task: {task_id}] [BochaSearch] 异常: {str(e)}")
            return []
