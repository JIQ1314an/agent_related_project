import json
from typing import Any, List, Dict, Optional  # 修复：补齐 missing import
from openai import OpenAI
from config import config
from logger import logger, log_step, log_error

class QwenLLMClient:
    """通义千问 Qwen3.7-Plus 客户端封装"""

    def __init__(self):
        log_step("LLMClient.init", f"初始化 QwenLLMClient, Endpoint: {config.QWEN_BASE_URL}, Model: {config.MODEL_NAME}")
        self.client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY,
            base_url=config.QWEN_BASE_URL
        )
        self.model = config.MODEL_NAME

    def one_shot_chat(self, prompt: str) -> str:
        """单次问答接口"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            log_error("LLMClient.one_shot_chat", f"调用 Qwen API 失败: {str(e)}")
            raise e

    def chat_with_tools(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        """带 Tools 参数的 Agent 对话接口"""
        log_step("LLMClient.chat_with_tools", f"请求 LLM, 当前 Message 长度: {len(messages)}, 工具数量: {len(tools) if tools else 0}")
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            log_step("LLMClient.response", f"LLM 响应 Finish Reason: {choice.finish_reason}")
            return choice.message
        except Exception as e:
            log_error("LLMClient.chat_with_tools", f"调用 Qwen API 失败: {str(e)}")
            raise e