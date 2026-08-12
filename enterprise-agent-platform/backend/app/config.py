import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    企业级Agent平台全局配置管理
    读取环境变量并提供强类型保障
    """

    PROJECT_NAME: str = "Enterprise Agent Platform"
    VERSION: str = "1.0.0"

    # 通义千问 Qwen 3.7 Plus 配置 (通过 DashScope OpenAI 兼容接口访问)
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "your-dashscope-key")
    QWEN_MODEL_NAME: str = "qwen3.7-plus"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 存储配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://agent_user:agent_pass@localhost:5432/agent_db"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # LangFuse 可观测性配置
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    # Harness Loop 执行参数控制
    MAX_LOOP_RETRIES: int = 3
    SANDBOX_TIMEOUT_SECONDS: int = 10


settings = Settings()
