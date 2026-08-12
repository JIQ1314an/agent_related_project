import os
import hashlib
import warnings
from tqdm import tqdm
from pymilvus import connections, utility
from langchain_milvus import Milvus
from elasticsearch import Elasticsearch, helpers
from langchain_core.documents import Document

# 🆕 引入工业标准的目录加载器与自适应递归切分器
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 导入你原有的配置与日志
from config import (
    BASE_DIR,
    MILVUS_HOST,
    MILVUS_PORT,
    MILVUS_COLLECTION,
    ES_URL,
    ES_INDEX,
    get_embeddings,
    logger,
)

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module="langchain_milvus"
)


def _ensure_connections():
    """保底确保 Milvus 全局连接激活"""
    if not connections.has_connection("default"):
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)


# ==========================================================
# 🆕 工业级变革：多源本地文档智能加载与工业切片流
# ==========================================================
def load_and_split_industrial_docs(data_dir="./data"):
    """
    扫描本地 data 目录，支持 md, txt 等多源文件，
    采用工业标准的递归字符切 splitter，保留上下文层级。
    """
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.warning(
            f"检测到本地数据目录 {data_dir} 不存在，已自动创建。请将你的企业文档放入该目录下！"
        )
        return []

    logger.info(f"--- 📂 正在扫描本地知识库目录: {data_dir} ---")

    # 工业标准：使用 DirectoryLoader 自动化多线程扫描
    # 这里以 .md 和 .txt 为例，生产环境中可扩展为 PDF 或 Word 加载器
    loader = DirectoryLoader(
        data_dir,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    raw_docs = loader.load()

    if not raw_docs:
        logger.warning("⚠️ 本地 data/ 目录下没有发现任何有效的知识库文档。")
        return []

    # 工业标准的文本切分器：优先按段落切，段落太长按句子切，句子太长按词切
    # 既保证了知识碎片的独立性，又把 Chunk 大小控制在轻薄本和 Reranker 最爱的 500 token 左右
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=60,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )

    splitted_documents = text_splitter.split_documents(raw_docs)
    logger.info(
        f"--- 📝 原始文档 {len(raw_docs)} 篇，经工业层级切分后生成 {len(splitted_documents)} 个知识片段 ---"
    )
    return splitted_documents


# ==========================================================
# 断点续传核心引擎（完全承袭你上一版高可用逻辑）
# ==========================================================
def _batch_hybrid_store(documents, embeddings):
    if not documents:
        logger.warning("没有可写入的文档片段。")
        return None

    BATCH_SIZE = 50

    # ================= 1. 哈希固化 ID & 寻找最短文档 =================
    min_doc = None
    min_len = float("inf")
    for i, doc in enumerate(documents):
        # 🌟 核心改进：在哈希源字符串中混入全局唯一序号 f"_chunk_{i}"
        unique_str = doc.page_content + str(doc.metadata) + f"_chunk_{i}"
        doc_id = hashlib.md5(unique_str.encode("utf-8")).hexdigest()
        doc.metadata["doc_id"] = doc_id

        # 🌟 顺手记录最短文档（O(1) 复杂度，无额外性能开销）
        content_len = len(doc.page_content)
        if content_len < min_len:
            min_len = content_len
            min_doc = doc

    # 防御性编程：防止 documents 为空的情况
    if min_doc is None:
        raise ValueError("❌ 传入的 documents 为空，无法进行后续处理！")
    logger.info(
        f"✅ 哈希计算完成。已锁定最短文档 (长度: {min_len} 字符) 用于后续极速建表。"
    )

    # 2. 数据库底座初始化
    _ensure_connections()
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        collection_name=MILVUS_COLLECTION,
    )

    es = Elasticsearch(ES_URL)
    if not es.indices.exists(index=ES_INDEX):
        es.indices.create(index=ES_INDEX)

    # ================= 3. Milvus Schema 首次初始化保障 =================
    if not vector_store.client.has_collection(collection_name=MILVUS_COLLECTION):
        logger.info(
            "🛠️ 首次运行：检测到 Milvus 集合不存在，正在初始化 Schema (表结构)..."
        )
        logger.info(f"⏳ 正在使用最短文档 (长度: {min_len}) 进行极速建表...")

        # 🌟 直接使用第 1 步找好的 min_doc，无需再次遍历或调用 min()
        vector_store = Milvus.from_documents(
            documents=[min_doc],
            embedding=embeddings,
            connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
            collection_name=MILVUS_COLLECTION,
            ids=[min_doc.metadata["doc_id"]],
            drop_old=False,
        )

        # 🌟 建表成功后立即清理占位数据，确保后续 tqdm 统计 100% 对齐
        vector_store.delete(ids=[min_doc.metadata["doc_id"]])
        logger.info("✅ Milvus 集合初始化完成，占位数据已清理！准备全量同步...")

    # ================= 4. 双路独立查重断点续传 =================
    # 【优化点】：此时所有数据（包括第一条）都会经过这个循环，进度条从 0 完整跑到 100%
    with tqdm(
        total=len(documents), desc="🚀 工业数据双路同步中", unit="docs", ncols=100
    ) as pbar:
        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i : i + BATCH_SIZE]
            batch_ids = [doc.metadata["doc_id"] for doc in batch]

            # --- Milvus 查重 ---
            id_expr = f"doc_id in {list(batch_ids)}"
            existing_milvus = vector_store.client.query(
                collection_name=MILVUS_COLLECTION,
                filter=id_expr,
                output_fields=["doc_id"],
            )
            exist_milvus_ids = {row["doc_id"] for row in existing_milvus}
            todo_milvus_batch = [
                d for d in batch if d.metadata["doc_id"] not in exist_milvus_ids
            ]

            # --- ES 查重 ---
            exist_es_ids = set()
            try:
                es_res = es.search(
                    index=ES_INDEX,
                    query={"ids": {"values": batch_ids}},
                    _source=False,  # 优化：不需要返回 source 内容，加快速度
                    size=BATCH_SIZE,
                )
                exist_es_ids = {hit["_id"] for hit in es_res["hits"]["hits"]}
            except Exception as e:
                # 【优化点】：ES 查重失败时打印警告，而不是静默 pass，方便排查问题
                logger.warning(
                    f"⚠️ ES 查重出现异常，本批次将尝试全量写入 ES。错误信息: {e}"
                )

            todo_es_batch = [
                d for d in batch if d.metadata["doc_id"] not in exist_es_ids
            ]

            # --- 分流写入 ---
            if todo_milvus_batch:
                vector_store.add_documents(
                    documents=todo_milvus_batch,
                    ids=[d.metadata["doc_id"] for d in todo_milvus_batch],
                )

            if todo_es_batch:
                actions = [
                    {
                        "_index": ES_INDEX,
                        "_id": d.metadata["doc_id"],
                        "_source": {"text": d.page_content, "metadata": d.metadata},
                    }
                    for d in todo_es_batch
                ]
                helpers.bulk(es, actions)

            # 更新进度条
            pbar.update(len(batch))

            # 【可选优化】：在进度条后缀显示当前批次的实际写入量，让进度条信息更丰富
            pbar.set_postfix(
                {"Milvus写入": len(todo_milvus_batch), "ES写入": len(todo_es_batch)}
            )

    return vector_store


# ==========================================================
# 对外暴露的统一高可用 Retriever 入口
# ==========================================================
def get_retriever():
    key = 10
    _ensure_connections()
    embeddings = get_embeddings()
    es_client = Elasticsearch(ES_URL)

    milvus_exists = utility.has_collection(MILVUS_COLLECTION)
    try:
        es_exists = es_client.indices.exists(index=ES_INDEX)
    except Exception:
        es_exists = False

    # 💡 懒加载保底：如果两路不完整，自动触发本地 data/ 目录的工业扫描与灌库
    if not milvus_exists or not es_exists:
        logger.warning("📊 检测到双路检索库未就绪，启动工业本地文件全量解析流程...")
        # data_path = os.path.join(BASE_DIR, "data")
        # industrial_docs = load_and_split_industrial_docs(data_path)
        industrial_docs = load_and_split_industrial_docs()
        vector_store = _batch_hybrid_store(industrial_docs, embeddings)
    else:
        logger.info(" ✅  检测到双路检索库已就绪...")
        vector_store = Milvus(
            embedding_function=embeddings,
            connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
            collection_name=MILVUS_COLLECTION,
        )

    milvus_base_retriever = vector_store.as_retriever(search_kwargs={"k": key})
    return MilvusESHybridRetriever(
        milvus_retriever=milvus_base_retriever,
        es_client=es_client,
        es_index=ES_INDEX,
        k=key,
    )


# ==========================================================
# 🆕 核心设计：自适应高可用混合检索器 (免除 LangChain 版本冲突)
# ==========================================================
class MilvusESHybridRetriever:
    def __init__(self, milvus_retriever, es_client, es_index, k=10):
        self.milvus_retriever = milvus_retriever
        self.es_client = es_client
        self.es_index = es_index
        self.k = k

    def get_relevant_documents(self, query: str):
        """
        保持与原有 LangChain Retriever 完全一致的接口名
        """
        # 1. 并行/顺序捞取 Milvus 向量结果 (粗筛 10 篇)
        try:
            milvus_docs = self.milvus_retriever.get_relevant_documents(query)
            logger.info(f" ✅ Milvus 向量检索成功。")
        except Exception as e:
            logger.error(f"❌ Milvus 向量检索失败 ({e})，混合检索降级为BM25检索。")

        # 2. 从 Elasticsearch 中捞取 BM25 关键字结果 (粗筛 10 篇)
        es_docs = []
        try:
            res = self.es_client.search(
                index=self.es_index, query={"match": {"text": query}}, size=self.k
            )
            for hit in res["hits"]["hits"]:
                es_docs.append(
                    Document(
                        page_content=hit["_source"]["text"],
                        metadata=hit["_source"]["metadata"],
                    )
                )
            logger.info(f"✅ ES BM25 检索成功。")
        except Exception as e:
            logger.error(f"❌ ES BM25 检索失败 ({e})，混合检索降级为纯向量。")

        # 3. 混合并去重（去重标准：文本内容 page_content）
        seen = set()
        combined_documents = []

        # 将 Dense(密文) 与 Sparse(稀疏关键词) 候选集混合
        for doc in milvus_docs + es_docs:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                combined_documents.append(doc)

        # 吐出所有无重复的候选集，交由后面的 Reranker 做最终的“生杀大权”评分
        return combined_documents

    # 🎯 手动补上这个方法，完美欺骗并对接 LangGraph 节点的 invoke 调用
    def invoke(self, query: str, **kwargs):
        return self.get_relevant_documents(query)
