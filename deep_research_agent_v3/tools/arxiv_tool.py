import re
import requests
import xml.etree.ElementTree as ET
from typing import List
from logger import logger
from models import SearchResultItem


class ArxivSearchTool:
    """arXiv 前沿论文检索工具 (基于原生 requests + XML 解析，零额外 SDK 依赖)"""

    BASE_URL = "http://export.arxiv.org/api/query"

    def _contains_chinese(self, text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fa5]", text))

    def search(
        self, query: str, task_id: str = "SYS", max_results: int = 2
    ) -> List[SearchResultItem]:
        # 1. 中文提示防护
        if self._contains_chinese(query):
            logger.warning(
                f"[Task: {task_id}] [arXivSearch] 检测到中文 query: '{query}'，arXiv 对中文支持极差，建议使用英文关键词。"
            )

        logger.info(f"[Task: {task_id}] [arXivSearch] 发起 arXiv 论文检索: '{query}'")

        try:
            # 2. 构造 arXiv 官方 Atom API 参数
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
            # 设置伪装 User-Agent，避免被 arXiv 防火墙阻断
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            # 3. 发起请求 (使用 HTTP 端口或增加 timeout，防止 SSL 崩溃)
            response = requests.get(
                self.BASE_URL, params=params, headers=headers, timeout=12
            )
            if response.status_code != 200:
                logger.error(
                    f"[Task: {task_id}] [arXivSearch] 请求失败，状态码: {response.status_code}"
                )
                return []

            # 4. 解析 arXiv 返回的 Atom XML 数据
            root = ET.fromstring(response.content)
            # Atom 命名空间
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            results = []
            for entry in root.findall("atom:entry", ns):
                raw_title = entry.find("atom:title", ns).text or ""
                raw_summary = entry.find("atom:summary", ns).text or ""
                raw_id = entry.find("atom:id", ns).text or ""
                raw_published = entry.find("atom:published", ns).text or ""

                # 格式化清洗
                title = " ".join(raw_title.split())
                summary = " ".join(raw_summary.split())
                publish_date = (
                    raw_published[:7] if len(raw_published) >= 7 else "Unknown"
                )

                content = (
                    f"[arXiv 论文摘要]: {summary[:500]}... | 发表时间: {publish_date}"
                )

                results.append(
                    SearchResultItem(
                        title=f"[Academic] {title}",
                        url=raw_id,
                        content=content,
                        score=0.85,
                        source_type="arxiv",
                    )
                )

            logger.info(
                f"[Task: {task_id}] [arXivSearch] 成功解析获取到 {len(results)} 篇论文。"
            )
            return results

        except Exception as e:
            # 网络或解析异常降级处理
            logger.error(f"[Task: {task_id}] [arXivSearch] 检索异常: {str(e)}")
            return []
