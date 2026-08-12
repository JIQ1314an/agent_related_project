import sys
from pathlib import Path
from typing import Dict, Any, Optional
from logger import get_task_logger

log = get_task_logger("OBSERVABILITY")


class TelemetryTracker:
    """工业级可观测性包装器：自带熔断机制，追踪失败时自动降级，绝不阻塞主业务"""

    def __init__(self):
        self.client = None
        try:
            from config import config
            from langfuse import Langfuse

            if config.LANGFUSE_PUBLIC_KEY and config.LANGFUSE_SECRET_KEY:
                self.client = Langfuse(
                    public_key=config.LANGFUSE_PUBLIC_KEY,
                    secret_key=config.LANGFUSE_SECRET_KEY,
                    host=config.LANGFUSE_HOST,
                )
                log.info("Langfuse 可观测性客户端初始化成功")
        except Exception as e:
            log.warning(f"Langfuse 初始化跳过/失败，已降级为静默模式: {e}")

    def log_generation(
        self,
        task_id: str,
        name: str,
        input_prompt: str,
        output_text: str,
        usage: Dict[str, int],
        model: str,
    ):
        """安全记录 LLM 调用数据"""
        if not self.client:
            return
        try:
            # 兼容 Langfuse v2/v3 SDK API
            if hasattr(self.client, "generation"):
                self.client.generation(
                    name=name,
                    model=model,
                    input=input_prompt,
                    output=output_text,
                    usage=usage,
                    metadata={"task_id": task_id},
                )
        except Exception as e:
            log.warning(f"Langfuse 记录 Generation 失败 (已静默忽略): {e}")

    def flush(self):
        """推送缓存日志"""
        if self.client:
            try:
                self.client.flush()
            except Exception as e:
                log.warning(f"Langfuse Flush 失败: {e}")


telemetry = TelemetryTracker()
