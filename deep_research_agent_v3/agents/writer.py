import os
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config import settings
from logger import logger
from prompts import (
    WRITER_TECH_SYSTEM_PROMPT,
    WRITER_PHILOSOPHY_SYSTEM_PROMPT,
    WRITER_GENERAL_SYSTEM_PROMPT,
)


class ReportWriterAgent:
    """[Agent 3] Report Writer: 根据分类选择专属 Prompt，并结合多源情报与审查反馈撰写报告"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            # openai_api_key=settings.OPENAI_API_KEY,
            # openai_api_base=settings.OPENAI_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            temperature=0.3,
        )

    def run(
        self,
        topic: str,
        analyzed_docs: Any,
        task_id: str = "SYS",
        feedback: str = "",
        category: str = "general",
    ) -> str:
        logger.info(
            f"[Task: {task_id}] [WriterAgent] 开始撰写报告 | 课题分类: {category} | 是否有审查反馈: {bool(feedback)}"
        )

        # 根据 Planner 识别出的 category 动态匹配专属 Prompt
        if category == "tech":
            system_prompt = WRITER_TECH_SYSTEM_PROMPT.format(
                min_word_count=settings.MIN_WORD_COUNT
            )
        elif category == "philosophy":
            system_prompt = WRITER_PHILOSOPHY_SYSTEM_PROMPT.format(
                min_word_count=settings.MIN_WORD_COUNT
            )
        else:
            system_prompt = WRITER_GENERAL_SYSTEM_PROMPT.format(
                min_word_count=settings.MIN_WORD_COUNT
            )

        user_content = f"研究课题: {topic}\n\n【资料与情报】:\n{analyzed_docs}\n"

        # 保留你的修改迭代逻辑：如果有上一轮 Reviewer 的意见，拼接到 Prompt 中
        if feedback:
            user_content += (
                f"\n【上一轮审查反馈意见 (请针对性修复并完善)】:\n{feedback}\n"
            )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            response = self.llm.invoke(messages)
            print(
                f"=== Writer ===\nmessage: 【{messages}】\n\n response: 【{response}】"
            )
            report_text = response.content
            logger.info(
                f"[Task: {task_id}] [WriterAgent] 报告撰写完成，总字数约: {len(report_text)} 字符"
            )
            return report_text
        except Exception as e:
            logger.error(
                f"[Task: {task_id}] [WriterAgent] 撰写报告失败: {str(e)}", exc_info=True
            )
            raise
