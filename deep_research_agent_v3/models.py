from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


# 1. 在 models.py 中直接定义工具枚举 (底层数据类型)
class ToolType(str, Enum):
    WEB = "web"
    BOCHA = "bocha"
    ARXIV = "arxiv"
    GITHUB = "github"


# 2. 基础搜索结果模型
class SearchResultItem(BaseModel):
    title: str
    url: str
    content: str
    score: float = 0.0
    source_type: str = "web"


# 3. 研究子任务模型 (直接使用 ToolType)
class ResearchSubTask(BaseModel):
    title: str = Field(description="子研究课题标题")
    query: str = Field(description="用于搜索引擎检索的精确关键词/短语")
    rationale: str = Field(description="该子检索项的必要性与目标")
    source_types: List[ToolType] = Field(default_factory=lambda: [ToolType.WEB])


class ResearchPlan(BaseModel):
    category: str = Field(
        description="课题分类标签: 严格从 ['tech', 'philosophy', 'business', 'general'] 中选择一个"
    )
    sub_tasks: List[ResearchSubTask] = Field(description="包含 3 到 5 个子研究任务")
    overview: str = Field(description="研究计划的总体思路")


class SearchResultItem(BaseModel):
    """搜索引擎返回的单条文档元数据"""

    title: str
    url: str
    content: str
    score: float = 0.0
    source_type: str = "web"  # 新增数据源标识: "web", "arxiv", "github"


class AnalyzedDoc(BaseModel):
    """经过分析器提炼后的子课题结构化情报"""

    sub_task_title: str
    key_insights: List[str] = Field(description="提炼的核心技术观点与数据")
    citations: List[Dict[str, str]] = Field(
        description="引用的源网页信息 [{'title': ..., 'url': ...}]"
    )


from typing import List
from pydantic import BaseModel, Field


class QualityReview(BaseModel):
    """报告质量审查结果"""

    passed: bool = Field(
        description="报告是否合格通过。若无严重逻辑缺失，建议给予 True"
    )
    score: float = Field(default=85.0, description="综合评分 (0-100)")
    word_count: int = Field(description="评估报告的大致总字数")
    missing_aspects: List[str] = Field(
        default_factory=list,
        description="缺失或需要补充的关键维度列表（每项简短列出，不超过 20 字，切勿写长段落）",
    )
    feedback: str = Field(
        description="总结性修改意见，控制在 300 字以内，切勿复制或引用报告原文！"
    )


class State(BaseModel):
    """LangGraph 节点间传递的全局状态模型"""

    task_id: str = "SYS-DEFAULT"  # 核心新增: 全局任务 ID/Thread ID，用于并发日志隔离
    topic: str
    plan: Optional[ResearchPlan] = None
    search_results: Dict[str, List[SearchResultItem]] = Field(default_factory=dict)
    analyzed_docs: List[AnalyzedDoc] = Field(default_factory=list)
    report_draft: str = ""
    review: Optional[QualityReview] = None
    iteration_count: int = 0
    final_report: str = ""
