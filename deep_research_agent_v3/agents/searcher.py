from typing import Dict, List
from models import ResearchPlan, SearchResultItem
from tools.registry import tool_registry  # 直接使用中央注册表
from logger import logger


class WebSearcherAgent:
    """[Agent 2] Web Searcher: 依靠 ToolRegistry 调度工具，不关注底层实现细节"""

    def run(
        self, plan: ResearchPlan, task_id: str = "SYS"
    ) -> Dict[str, List[SearchResultItem]]:
        logger.info(f"[Task: {task_id}] [SearcherAgent] 启动多源工具联合智能检索...")
        all_results = {}

        for task in plan.sub_tasks:
            sources_str = [st.value for st in task.source_types]
            logger.info(
                f"[Task: {task_id}] [SearcherAgent] 执行子任务: '{task.title}' | 目标通道: {sources_str}"
            )
            sub_task_results = []

            for tool_type in task.source_types:
                # 核心：从注册表直接获取工具实例
                tool = tool_registry.get_tool_instance(tool_type)
                if not tool:
                    logger.warning(
                        f"[Task: {task_id}] [SearcherAgent] 注册表中未找到类型为 '{tool_type}' 的工具实例，自动跳过。"
                    )
                    continue

                # 控水策略：单通道限制 2 条以内，控制上下文长度
                items = tool.search(task.query, task_id=task_id, max_results=2)
                sub_task_results.extend(items)

            all_results[task.title] = sub_task_results

        logger.info(
            f"[Task: {task_id}] [SearcherAgent] 智能多源检索完毕，涵盖 {len(all_results)} 个子课题。"
        )
        print(f"子课题具体内容：【{all_results}】")
        return all_results
