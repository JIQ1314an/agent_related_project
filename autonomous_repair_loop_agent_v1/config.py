import os
from dataclasses import dataclass
from dotenv import load_dotenv

# 显式加载 .env 文件中的配置项
load_dotenv()


@dataclass
class Config:
    # Qwen API 配置 (使用 OpenAI 兼容接口)
    QWEN_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "your-dashscope-api-key")
    QWEN_BASE_URL: str = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3.7-plus")

    # Langfuse 追踪配置
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000")

    # Agent Loop 控制
    MAX_REPAIR_ATTEMPTS: int = 5
    EXECUTION_TIMEOUT: int = 10  # 单次执行超时时间(秒)


config = Config()

# 基础启动校验
if not config.QWEN_API_KEY:
    raise ValueError("未检测到 DASHSCOPE_API_KEY，请检查 .env 文件或系统环境变量设置。")
# else:
#     print("QWEN_API_KEY：", config.QWEN_API_KEY)
