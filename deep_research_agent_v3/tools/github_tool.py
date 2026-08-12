import requests
from typing import List
from logger import logger
from models import SearchResultItem


class GithubSearchTool:
    """GitHub REST API 封装，用于检索开源 Agent 框架与仓库数据"""

    BASE_URL = "https://api.github.com/search/repositories"

    def search(
        self, query: str, task_id: str = "SYS", max_results: int = 2
    ) -> List[SearchResultItem]:
        logger.info(f"[Task: {task_id}] [GitHubSearch] 发起开源仓库检索: '{query}'")
        try:
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results,
            }
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DeepResearchAgent",
            }
            resp = requests.get(
                self.BASE_URL, params=params, headers=headers, timeout=8
            )

            if resp.status_code != 200:
                logger.warning(
                    f"[Task: {task_id}] [GitHubSearch] 请求响应状态码: {resp.status_code}"
                )
                return []

            data = resp.json()
            results = []
            for item in data.get("items", []):
                repo_name = item.get("full_name", "")
                stars = item.get("stargazers_count", 0)
                description = item.get("description", "") or "无描述"
                html_url = item.get("html_url", "")

                snippet = f"[GitHub 仓库] Star 数: {stars} | 描述: {description[:250]}"
                results.append(
                    SearchResultItem(
                        title=f"[GitHub] {repo_name}",
                        url=html_url,
                        content=snippet,
                        score=0.95,
                        source_type="github",
                    )
                )

            logger.info(
                f"[Task: {task_id}] [GitHubSearch] 获取到 {len(results)} 个 GitHub 项目。"
            )
            return results
        except Exception as e:
            logger.error(f"[Task: {task_id}] [GitHubSearch] 异常: {str(e)}")
            return []
