from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from prompts import PLANNER_SYSTEM_PROMPT
from config import settings
from logger import logger
from models import ResearchPlan
from tools.registry import tool_registry  # 导入注册表


class ResearchPlannerAgent:
    """[Agent 1] Research Planner: 结合 ToolRegistry 动态感知可用工具并规划任务"""

    # Planner 不再写死任何 Tool 的名字和描述，而是向 tool_registry 动态拉取
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            # openai_api_key=settings.OPENAI_API_KEY,
            # openai_api_base=settings.OPENAI_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            temperature=0.2,
        )
        self.structured_llm = self.llm.with_structured_output(ResearchPlan)

    def run(self, topic: str, task_id: str = "SYS", feedback: str = "") -> ResearchPlan:
        logger.info(
            f"[Task: {task_id}] [PlannerAgent] 开始为课题制定/修订研究计划: '{topic}'"
        )

        # 核心：从注册表中动态提取当前“已注册”的所有工具说明
        dynamic_tools_desc = tool_registry.get_tools_prompt_description()

        # system_prompt = (
        #     "你是一个资深的前沿科技与产业研究规划专家。你的任务是将一个复杂的课题拆解为 "
        #     "3 到 5 个高度互补的子研究方向，并为每个方向指定最匹配的数据检索通道 (source_types)。\n\n"
        #     f"【当前系统集成的可用工具库】:\n{dynamic_tools_desc}\n\n"
        #     "请严格根据各子任务的侧重点，选择最合适的工具通道列表。\n"
        #     "【重要约束】:\n"
        #     "1. 若子任务的 source_types 包含 'arxiv'，则该子任务的 query **必须使用标准的英文学术关键词**（如将 '大模型幻觉' 写为 'LLM hallucination'）。\n"
        #     "2. 其它通道（如 bocha、web）可继续使用中文或英文 query。"
        # )

        system_prompt = PLANNER_SYSTEM_PROMPT.format(
            dynamic_tools_desc=dynamic_tools_desc
        )

        user_content = f"研究课题: {topic}\n"
        if feedback:
            user_content += f"历史报告审核意见 (请在拆解中针对性修复): {feedback}\n"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            plan = self.structured_llm.invoke(messages)
            print(f"=== Planner ===\nmessage: 【{messages}】\n\n plan: 【{plan}】")
            logger.info(
                f"[Task: {task_id}] [PlannerAgent] 拆解出 {len(plan.sub_tasks)} 个子任务。"
            )
            for sub in plan.sub_tasks:
                # sub.source_types 此时是 ToolType 枚举列表，打印其 value
                sources = [st.value for st in sub.source_types]
                logger.info(
                    f"[Task: {task_id}] [PlannerAgent] 子任务: '{sub.title}' -> 选中通道: {sources}"
                )
            return plan
        except Exception as e:
            logger.error(
                f"[Task: {task_id}] [PlannerAgent] 生成研究计划失败: {str(e)}",
                exc_info=True,
            )
            raise
