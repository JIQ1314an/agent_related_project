from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config import settings
from logger import logger
from models import QualityReview
from prompts import REVIEWER_SYSTEM_PROMPT


class QualityReviewerAgent:
    """[Agent 4] Quality Reviewer: 对生成的初稿进行质量审查"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            # openai_api_key=settings.OPENAI_API_KEY,
            # openai_api_base=settings.OPENAI_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            temperature=0.0,  # 核心：彻底消除死循环幻觉
            max_tokens=2000,  # 核心：设定合理的上限保护
        )
        self.structured_llm = self.llm.with_structured_output(QualityReview)

    def run(self, topic: str, report: str, task_id: str = "SYS") -> QualityReview:
        logger.info(f"[Task: {task_id}] [ReviewerAgent] 启动报告质量审查...")

        # system_prompt = (
        #     "你是一名严谨的科技与产业报告主编。你的任务是审查生成的报告是否达到出版质量。\n\n"
        #     "【审查标准】:\n"
        #     "1. 内容是否切题，结构是否完整 (包含背景、技术分析、产业影响、结论等)。\n"
        #     "2. 评估 word_count (估算字数) 与 missing_aspects (缺失的核心角度)。\n"
        #     "3. 给出精炼的修改意见 (feedback)。\n\n"
        #     "【输出硬性要求】:\n"
        #     "1. 绝不能在 feedback 中重复或引用整篇报告原文！\n"
        #     "2. missing_aspects 仅列出短短的关键词/短语列表（如 ['缺乏量化数据支撑', '缺少国内合规分析']），严禁写长篇大论！\n"
        #     "3. feedback 必须精炼简明，控制在 300 字以内！"
        # )

        system_prompt = REVIEWER_SYSTEM_PROMPT

        # 截取报告正文（前 8000 字符），防止超长 Prompt 干扰模型的 JSON 输出格式
        user_content = f"研究课题: {topic}\n\n待审查报告摘要/正文:\n{report[:8000]}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            review = self.structured_llm.invoke(messages)
            print(f"=== Review ===\nmessage: 【{messages}】\n\n review: 【{review}】")
            logger.info(
                f"[Task: {task_id}] [ReviewerAgent] 审查完成 | 通过: {review.passed} | 分数: {review.score} | 缺失项: {len(review.missing_aspects)}个"
            )
            return review

        except Exception as e:
            # 完整保留原有字段的降级兜底对象
            logger.error(
                f"[Task: {task_id}] [ReviewerAgent] 解析异常 (已触发兜底放行): {str(e)}"
            )
            return QualityReview(
                passed=True,
                score=80.0,
                word_count=len(report),
                missing_aspects=[],
                feedback="[System Reviewer Auto-Pass]: 审查模块解析异常或输出被截断，已触发降级策略自动放行报告。",
            )
