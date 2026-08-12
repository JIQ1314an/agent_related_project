import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 加载环境配置文件
load_dotenv()


class Settings(BaseSettings):
    """全局项目配置项"""

    # DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_API_KEY: str = (
        os.environ.get("DASHSCOPE_API_KEY")
        if "DASHSCOPE_API_KEY" in os.environ
        else os.getenv("DASHSCOPE_API_KEY", "")
    )
    QWEN_BASE_URL: str = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3.7-plus")

    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000")

    MAX_LOOP_ITERATIONS: int = int(os.getenv("MAX_LOOP_ITERATIONS", "5"))
    SANDBOX_TIMEOUT_SECONDS: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "10"))


settings = Settings()

# print(settings.DASHSCOPE_API_KEY)
