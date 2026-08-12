import os
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局系统配置项管理"""

    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    ## 采用此，若执行 settings = Settings()，Pydantic 开始实例化，.env内容会覆盖系统环境变量的内容
    # QWEN_API_KEY: str = (
    #     os.environ.get("DASHSCOPE_API_KEY")
    #     if "DASHSCOPE_API_KEY" in os.environ
    #     else os.getenv("QWEN_API_KEY", "")
    # )

    # LLM 配置
    # 告诉 Pydantic：优先找 DASHSCOPE_API_KEY，找不到再找 QWEN_API_KEY
    # 它会自动在“系统环境变量”和“.env文件”中按此顺序查找
    QWEN_API_KEY: str = Field(
        default="", validation_alias=AliasChoices("DASHSCOPE_API_KEY", "QWEN_API_KEY")
    )
    QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen3.7-max-2026-05-17")

    # 全球搜索引擎 API Key
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    # 国内博查搜索引擎 API Key (可选)
    BOCHA_API_KEY: str = os.getenv("BOCHA_API_KEY", "")

    # LangFuse 监控配置
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # 系统运行控制参数
    MAX_REVISION_LOOPS: int = os.getenv(
        "MAX_REVISION_LOOPS", 2
    )  # 最大自我修正在循环次数
    MIN_WORD_COUNT: int = os.getenv("MAX_REVISION_LOOPS", 2000)  # 报告最小字数要求

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略多余的环境变量


settings = Settings()
