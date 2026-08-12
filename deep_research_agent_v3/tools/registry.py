from typing import Dict, Any
from models import ToolType  # 从 models 导入 ToolType
from tools.search_tool import TavilySearchTool
from tools.bocha_tool import BochaSearchTool
from tools.arxiv_tool import ArxivSearchTool
from tools.github_tool import GithubSearchTool


class ToolRegistry:
    """中央工具注册表：负责管理工具声明、动态生成 Prompt 描述以及工具实例调度"""

    def __init__(self):
        self._tools: Dict[ToolType, Dict[str, Any]] = {
            ToolType.WEB: {
                "name": ToolType.WEB.value,
                "description": "全球通用网页/新闻/技术博客/文档检索 (Tavily)，适合大多数通用技术趋势、行业新闻与官方文档。",
                "instance": TavilySearchTool(),
            },
            ToolType.BOCHA: {
                "name": ToolType.BOCHA.value,
                "description": "国内深度社区/微信公众号/知乎/国内技术博客与企业落地实践检索 (博查 AI)，适合中文课题及国内生态。",
                "instance": BochaSearchTool(),
            },
            ToolType.ARXIV: {
                "name": ToolType.ARXIV.value,
                "description": "前沿学术论文与理论研究检索 (arXiv)，适合算法原理、数学推导、论文对比与实验室成果（适用于 AI、量子、生物等全学科）。",
                "instance": ArxivSearchTool(),
            },
            ToolType.GITHUB: {
                "name": ToolType.GITHUB.value,
                "description": "开源项目/代码仓库/SDK/架构设计检索 (GitHub)，适合开源框架选型、代码库分析与开发者生态评估。",
                "instance": GithubSearchTool(),
            },
        }

    def get_tools_prompt_description(self) -> str:
        """动态反射：提取所有工具自身的 description，自动组装给 Planner"""
        lines = []
        for tool_id, meta in self._tools.items():
            lines.append(f"- 通道标识 `{tool_id.value}`: {meta['description']}")
        all_tools_desc = "\n".join(lines)
        print(f"所有工具自身的 description: 【{all_tools_desc}】] ")
        return all_tools_desc

    def get_tool_instance(self, tool_type: ToolType):
        """根据枚举直接获取工具实例"""
        return self._tools.get(tool_type, {}).get("instance")


# 全局工具注册表单例
tool_registry = ToolRegistry()
