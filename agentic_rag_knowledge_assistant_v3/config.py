import logging
import os
from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI

# 配置全局结构化日志输出，确保生产环境下可调试追踪
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("AgenticRAG")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HF_TOKEN = "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"

# 阿里云百炼大模型（通义千问）网关配置
WORKSPACE_ID = "llm-4wyxwbawaegb4be8"  # 替换为你的阿里云工作空间ID
API_BASE = f"https://{WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"  # 关键点：切换为阿里云的 OpenAI 兼容端点
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")
MODEL_NAME = "qwen3.6-flash-2026-04-16"  # 或者 deepseek-chat


# ==========================================================
# 🆕 进阶优化：Milvus 与 Xinference Reranker 配置
# ==========================================================

# 🆕 彻底修复版：使用原生 gRPC 协议连接，拒绝 http 协议头
MILVUS_HOST = "127.0.0.1"  # 宿主机直接连接 WSL2 的本地回环
MILVUS_PORT = "19530"  # Milvus 默认 gRPC 端口
MILVUS_COLLECTION = "test1_knowledge_assistant_collection"

# Xinference 部署在 WSL2 里，默认暴露 9997 端口
XINFERENCE_RERANK_URL = "http://localhost:9997/v1/rerank"
# 填入你在 Xinference Web 界面中注册启动的模型 UID
XINFERENCE_MODEL_UID = "bge-reranker-v2-m3"


# ==========================================================
# 🆕 混合检索：Elasticsearch BM25 配置
# ==========================================================
ES_URL = "http://localhost:9200"
ES_INDEX = "test1_knowledge_bm25_index"


def get_llm(model_name: str = MODEL_NAME, temperature: float = 0.0):
    """
    初始化 Qwen3.6-Flash 大模型底座。
    采用 OpenAI 兼容模式连接阿里 DashScope 或自建网关。
    """
    api_key = DASHSCOPE_API_KEY
    base_url = API_BASE

    if not api_key:
        logger.warning("未检测到 QWEN_API_KEY 环境变量，请在执行前导出该变量。")

    logger.info(f"当前使用的模型是 [{model_name}] ...")
    return ChatOpenAI(
        model=model_name,
        api_key=api_key or "mock_key",
        base_url=base_url,
        temperature=temperature,
        streaming=False,
    )


def get_embeddings():
    """
    初始化本地 Ollama 运行的 bge-m3 Embedding 模型。
    通过环境变量 OLLAMA_BASE_URL 支持容器化或跨机器分布式部署。
    """
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    logger.info(
        f"正在初始化本地 Ollama Embedding 引擎, 终结点: {ollama_url}, 模型: bge-m3"
    )

    return OllamaEmbeddings(model="bge-m3", base_url=ollama_url)
