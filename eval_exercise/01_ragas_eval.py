import sys
import types
import warnings
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import OpenAI
from datasets import Dataset

# ======================================================================
# 1. 环境净化：全局屏蔽所有烦人的 DeprecationWarning
# ======================================================================
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ======================================================================
# 2. 核心兼容与网络补丁 (极简且致命)
# ======================================================================
# 2.1 兼容 ragas 0.4.3 强制导入 vertexai 的历史遗留问题
try:
    import langchain_community.chat_models.vertexai  # noqa: F401
except ImportError:
    _stub = types.ModuleType("langchain_community.chat_models.vertexai")

    class ChatVertexAI:
        pass

    _stub.ChatVertexAI = ChatVertexAI
    sys.modules["langchain_community.chat_models.vertexai"] = _stub

# 2.2 【根治 Connection Error】限制 httpx 异步并发连接数
# DashScope 网关对高并发极度敏感，Ragas 默认并发会瞬间打爆连接池导致断连。
# 这里强制全局最大连接数为 2，让请求排队，彻底避免网关 Reset。
_original_async_init = httpx.AsyncClient.__init__


def _patched_async_init(self, *args, **kwargs):
    kwargs.setdefault(
        "limits", httpx.Limits(max_connections=2, max_keepalive_connections=2)
    )
    kwargs.setdefault("timeout", httpx.Timeout(120.0, connect=30.0))
    _original_async_init(self, *args, **kwargs)


httpx.AsyncClient.__init__ = _patched_async_init


# ======================================================================
# 3. 业务依赖导入
# ======================================================================
from langchain_openai import OpenAIEmbeddings as LangChainOpenAIEmbeddings
from ragas import evaluate
from ragas.llms import llm_factory
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    ContextPrecision,
    ContextRecall,
)
from ragas.run_config import RunConfig

# ======================================================================
# 4. 配置加载
# ======================================================================
load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE_URL = os.getenv("QWEN_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen-plus")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-v3")

if not API_KEY or not BASE_URL:
    raise ValueError("请在 .env 中配置 DASHSCOPE_API_KEY 和 QWEN_BASE_URL！")


# ======================================================================
# 5. 初始化 LLM 与 Embeddings (现代 Ragas 写法)
# ======================================================================
# 限制同步客户端的连接数
http_client = httpx.Client(
    limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
    timeout=httpx.Timeout(120.0, connect=30.0),
)

openai_client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    max_retries=10,  # 客户端级别疯狂重试
    timeout=120.0,
    http_client=http_client,
)

# 使用 Ragas 现代工厂函数，替代废弃的 LangchainLLMWrapper
evaluator_llm = llm_factory(model=MODEL_NAME, client=openai_client)

# 使用 LangChain 的 Embeddings，配合 check_embedding_ctx_length=False 绕过 Tokenizer 问题
evaluator_embeddings = LangChainOpenAIEmbeddings(
    model=EMBEDDING_MODEL_NAME,
    openai_api_key=API_KEY,
    openai_api_base=BASE_URL,
    timeout=120.0,
    max_retries=10,
    check_embedding_ctx_length=False,
)


# ======================================================================
# 6. 构造测试数据集
# ======================================================================
eval_dataset = Dataset.from_dict(
    {
        "question": [
            "Langfuse 如何配置 API Key？",
            "Python 中如何读取环境变量？",
        ],
        "contexts": [
            ["需要在 .env 文件中设置 LANGFUSE_PUBLIC_KEY 和 LANGFUSE_SECRET_KEY。"],
            ["使用 import os; os.getenv('KEY_NAME') 获取环境变量。"],
        ],
        "answer": [
            "你需要在 .env 文件中配置 LANGFUSE_PUBLIC_KEY 和 LANGFUSE_SECRET_KEY。",
            "可以通过 os.getenv('KEY_NAME') 读取环境变量。",
        ],
        "ground_truth": [
            "配置 LANGFUSE_PUBLIC_KEY 与 LANGFUSE_SECRET_KEY。",
            "使用 os.getenv() 获取。",
        ],
    }
)


# ======================================================================
# 7. 执行评估与持久化
# ======================================================================
def run_ragas_evaluation():
    print(f"🚀 开始运行 {MODEL_NAME} 模型驱动的 Ragas 评估...")

    metrics = [
        Faithfulness(llm=evaluator_llm),
        ResponseRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        ContextPrecision(llm=evaluator_llm),
        ContextRecall(llm=evaluator_llm),
    ]

    # 强制单线程 + 极高重试，配合 httpx patch，彻底锁死网络稳定性
    results = evaluate(
        dataset=eval_dataset,
        metrics=metrics,
        run_config=RunConfig(max_workers=1, timeout=180, max_retries=10, wait=10),
    )

    df_results = results.to_pandas()
    print("\n📊 评估成功完成，结果如下:")
    print(df_results)

    output_dir = Path("eval_outputs")
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / "ragas_eval_report.csv"
    df_results.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 结果已保存 CSV: {csv_path}")


if __name__ == "__main__":
    run_ragas_evaluation()
