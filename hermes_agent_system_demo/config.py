import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()


class Config:
    """系统全局配置类"""

    # 通义千问 Qwen3.7-Plus 配置
    DASHSCOPE_API_KEY: str = os.getenv(
        "DASHSCOPE_API_KEY", "your_dashscope_api_key_here"
    )
    # Qwen 兼容 OpenAI 协议的 Base URL
    QWEN_BASE_URL: str = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    # 核心模型名称指定为 qwen3.7-plus
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3.7-plus")

    # 系统运行参数
    MAX_ITERATIONS: int = 10  # Agent ReAct 最大循环次数
    SKILLS_DIR: str = os.path.join(os.path.dirname(__file__), "skills", "custom_skills")


config = Config()

# print(config.DASHSCOPE_API_KEY)
