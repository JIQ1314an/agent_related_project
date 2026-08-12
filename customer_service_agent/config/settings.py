import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录绝对路径计算
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据库存储路径配置
DB_PATH = os.path.join(BASE_DIR, "data", "customer_store.db")

# 智能客服 Agent 内存状态持久化路径配置
# LangGraph 会在数据库里自动建表，把每一步的 State 序列化成二进制（Blob）或 JSON 存进去。
AM_PATH = os.path.join(BASE_DIR, "data", "agent_memory.db")


# 阿里云百炼大模型（通义千问）网关配置
WORKSPACE_ID = "llm-4wyxwbawaegb4be8"  # 替换为你的阿里云工作空间ID
API_BASE = f"https://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"  # 关键点：切换为阿里云的 OpenAI 兼容端点
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")
MODEL_NAME = "qwen3.6-flash"  # 或者 deepseek-chat
