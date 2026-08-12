import time

import httpx  # 🆕 引入 HTTP 库用于呼叫 Xinference
from typing import List, Literal, TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from config import get_llm, logger, XINFERENCE_RERANK_URL, XINFERENCE_MODEL_UID
from vector_store import get_retriever

# =====================================================================
# 1. 强类型状态机定义与结构化输出 Schema
# =====================================================================


# 1. 🆕 修改状态定义，增量加入 raw_documents
class AgentState(TypedDict):
    query: str  # 原始输入用户查询
    current_query: str  # 当前迭代（可能经过改写）的查询
    needs_retrieval: bool  # 是否需要检索的分类标签

    raw_documents: List[str]  # 🆕 存储 Milvus + ES 去重后的 k1 ∈ [k, 2k] 篇粗筛结果
    # 保持不变：最终留给 LLM 生成和幻觉检查的 k2 篇精华
    documents: List[str]  # 检索出的上下文切片列表
    generation: str  # 大模型生成的回答
    retry_count: int  # 查询重试计数器
    is_relevant: bool  # 文档与查询相关性评估
    is_hallucination: bool  # 幻觉状态检查标签


class QueryAnalysisSchema(BaseModel):
    needs_retrieval: bool = Field(
        description="若查询需要依赖外部特定专属知识库事实数据（如SQuAD历史事实、专业学术定义、内部资料等）支撑回答则返回 True；若是日常问候、无意义闲聊、或询问实时天气等通用常识提问，返回 False。"
    )


class RelevanceCheckSchema(BaseModel):
    is_relevant: bool = Field(
        description="评估检索出的文档上下文是否包含足够、充要的信息以直接回答该查询。信息完整返回 True，缺失或不匹配返回 False。"
    )


class HallucinationCheckSchema(BaseModel):
    is_hallucination: bool = Field(
        description="比对生成的回答与检索上下文。如果回答中包含了任何文档中未提及的伪造事实或推导，返回 True（存在幻觉），完全忠实于上下文则返回 False。"
    )


# 初始化基础设施组件
llm = get_llm()
retriever = get_retriever()

# =====================================================================
# 2. 图工作流节点实现 (Nodes)
# =====================================================================


def analyze_query(state: AgentState):
    """节点：分析查询语义，决策是否启动知识库检索（强化 Prompt 判定边界）"""
    logger.info(f"[节点触发] 分析查询: '{state['query']}'")

    parser = PydanticOutputParser(pydantic_object=QueryAnalysisSchema)

    # 此处建立极其严格的对比提示词，防止 Qwen 盲目触发检索
    # 通用、非硬编码的私有知识库路由 Prompt
    prompt = PromptTemplate(
        template=(
            "你是一个高精度的企业级 RAG (检索增强生成) 查询意图分流专家。\n"
            "你的核心任务是判定：用户的查询是否需要查阅【本机构内部的私有专属知识库】才能获得准确答案。\n\n"
            "【分流核心逻辑】:\n"
            "人类的知识分为‘公开通用知识’与‘机构内部私有知识’。请根据以下特征进行深度辨析：\n\n"
            "🛑 场景 A：必须判定为【不需要检索 (False)】\n"
            "1. 日常闲聊与交互：问候、道谢、讲笑话、对诗或无意义的输入（如：'你好'、'推荐几个笑话'）。\n"
            "2. 实时及动态信息：天气、股票、当天新闻、时间等需要联网插件而非静态库的信息。\n"
            "3. 公开领域常识与通用学术/技术定义：任何可以在教科书、维基百科、公开技术文档中查到的概念（如：'什么是大模型的幻觉'、'什么是TCP三次握手'、'微积分基本公式'、'Python怎么写快速排序'）。\n"
            "   *注：这些通用知识大模型自身参数内已经完美具备，不需要也不应该去内部私有库中检索，避免引发错误捞取（False Positive）。*\n\n"
            "📌 场景 B：必须判定为【需要检索 (True)】\n"
            "1. 机构特有的规章制度：特定公司的差旅报销细则、考勤休假规定、行政审批流转节点、新员工入职指南等。\n"
            "2. 内部私有的技术与作业规范：特定工厂车间（如某特定编号车间）的特种设备操作规程、内部系统部署架构、私有代码库合并规范、特定安全预案等。\n"
            "3. 垂直领域的专有实体与档案：非公开的区域地理志、特定社区/街道的内部居委会名录、未公开的垂直赛事合规与选拔总纲等。\n"
            "   *注：当用户问题中包含了强烈的‘本公司’、‘内部规定’、‘某特定车间/部门’、‘特定私有业务’的暗示或明确指代时，必须触发检索。*\n\n"
            "{format_instructions}\n\n"
            "用户查询:\n{query}"
        ),
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        response = chain.invoke({"query": state["query"]})
        logger.info(f"意图识别结果: needs_retrieval={response.needs_retrieval}")
        return {
            "current_query": state["query"],
            "needs_retrieval": response.needs_retrieval,
            "retry_count": 0,
            "documents": [],
        }
    except Exception as e:
        logger.error(f"分析查询节点解析失败，触发安全降级(默认检索): {str(e)}")
        return {
            "current_query": state["query"],
            "needs_retrieval": True,
            "retry_count": 0,
            "documents": [],
        }


def direct_answer(state: AgentState):
    """节点：直接应答流（非知识库依赖问题）"""
    logger.info("[节点触发] 直接应答通道开启")
    response = llm.invoke(
        f"你是一个智能助手，请直接流畅地回答用户的日常互动、闲聊或无法由本地知识库提供支持的实时问题（如天气）：\n{state['query']}"
    )
    return {"generation": response.content}


# 2. 修改 retrieve 节点
def retrieve(state: AgentState):
    """节点：执行知识库检索获取上下文"""
    logger.info(f"[节点触发] 执行知识检索检索词: '{state['current_query']}'")
    # invoke 是 LangChain 框架自带的标准方法。它必须接收一个参数，这里是要查询的文本。
    # invoke 拿到你的查询文本，自动调用 embeddings 把这段文本变成向量， 去 milvus 数据库里匹配最接近的 10 个分块（由你的 k: 10 决定），并根据query去 es 里匹配最接近的 10 个分块（由你的 k 决定），最终把找到的文档（两次的融合去重，数量[k,2*k]）赋予 docs。
    docs = retriever.invoke(state["current_query"])
    # 提取纯文本字符串
    doc_texts = [doc.page_content for doc in docs]
    return {
        "raw_documents": doc_texts,  # ✅ 保持原样：给你的原有流程用
        "raw_documents_objs": docs,  # ➕ 新增影子通道：把带有元数据的完整对象传下去，专供评测
    }


def rerank(state: AgentState):
    """
    新增节点：通过重排模型从 10 篇中精选 key 篇
    """
    key = 3
    query = state["query"]
    raw_docs = state["raw_documents"]  # 纯文本列表
    raw_objs = state.get("raw_documents_objs", [])  # 影子对象列表

    if not raw_docs:
        return {"documents": []}

    # logger.info(f"query: {query}, documents: {raw_docs}")
    # 满足了 Xinference 只要纯文本的要求
    payload = {
        "model": XINFERENCE_MODEL_UID,
        "query": query,
        "documents": raw_docs,
    }

    # 针对首次加载或CPU运行，建议给予 连接阶段（Connect）10 秒，读取阶段（Read））360 秒的宽裕时间
    timeout_config = httpx.Timeout(360.0, connect=10.0)

    try:
        logger.info(f"⏳ 正在进行 Rerank ，请稍候...")
        start_time = time.time()
        response = httpx.post(
            XINFERENCE_RERANK_URL, json=payload, timeout=timeout_config
        )
        response.raise_for_status()
        elapsed_time = round(time.time() - start_time, 2)
        logger.info(f"✅ Rerank完成，[耗时: {elapsed_time}s]")

        results = response.json().get("results", [])
        # Xinference Rerank 返回的数据已经按得分从高到低排好，我们直接截取前 key
        # 💡 核心修改：利用 item["index"] 回源到 raw_docs 中获取真实的文本
        # 🌟 核心保留：依然给你的主通道塞【纯字符串列表】！
        # 这样你后面的 generate 等所有节点 100% 正常运行，不需要做任何修改！
        best_docs = [raw_docs[item["index"]] for item in results[:key]]

        # 🌟 影子通道：同步把对应的【完整对象】也切出来，供评测脚本无感知读取
        best_objs = (
            [raw_objs[item["index"]] for item in results[:key]] if raw_objs else []
        )

        return {
            "documents": best_docs,  # 给原有业务节点消费
            "documents_objs": best_objs,  # 给评测脚本消费（业务节点会自动忽略它）
        }
    except Exception as e:
        logger.warning(f"⚠️ Xinference 异常 ({e})，安全降级：直接截取前 key 篇")
        return {
            "documents": raw_docs[:key],
            "documents_objs": raw_objs[:key] if raw_objs else [],
        }


def check_relevance(state: AgentState):
    """节点：相关性粗筛网"""
    logger.info("[节点触发] 校验检索文档与当前查询的相关性")
    if not state["documents"]:
        return {"is_relevant": False}

    parser = PydanticOutputParser(pydantic_object=RelevanceCheckSchema)
    context_str = "\n---\n".join(state["documents"])

    prompt = PromptTemplate(
        template="请评估检索到的文档是否足以回答用户的查询。\n\n{format_instructions}\n\n用户查询: {query}\n\n检索到的参考上下文:\n{context}",
        input_variables=["query", "context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser
    try:
        res = chain.invoke({"query": state["current_query"], "context": context_str})
        logger.info(f"相关性检查结果: {res.is_relevant}")
        return {"is_relevant": res.is_relevant}
    except Exception as e:
        logger.warning(f"相关性检查解析异常，默认判断为不相关触发重试: {str(e)}")
        return {"is_relevant": False}


def rewrite_query(state: AgentState):
    """节点：改写用户查询，优化向量检索召回率"""
    current_retry = state["retry_count"] + 1
    logger.info(f"[节点触发] 启动查询改写机制。当前重试次数: {current_retry}")

    prompt = f"当前检索未命中匹配信息。为了在向量数据库中获得更高召回率，请将以下查询转换为针对搜索引擎优化后的关键词或意图扩展短语，直接输出改写后的文本，不要输出多余解释:\n{state['current_query']}"
    res = llm.invoke(prompt)
    return {"current_query": res.content.strip(), "retry_count": current_retry}


def generate_answer(state: AgentState):
    """节点：结合上下文生成严格受控的知识回答"""
    logger.info("[节点触发] 依据召回上下文生成最终回答")
    context_str = "\n---\n".join(state["documents"])
    prompt = f"请严格基于以下参考上下文回答用户问题。不要包含任何在上下文中未提及的推论或事实。\n\n上下文:\n{context_str}\n\n问题: {state['query']}\n\n请输出你的回答:"
    res = llm.invoke(prompt)
    return {"generation": res.content}


def check_hallucination(state: AgentState):
    """节点：对大模型回答执行严苛的幻觉校验拦截"""
    logger.info("[节点触发] 幻觉安全拦截检查中...")
    parser = PydanticOutputParser(pydantic_object=HallucinationCheckSchema)
    context_str = "\n---\n".join(state["documents"])

    prompt = PromptTemplate(
        template="请比对生成的回答与参考上下文，检查是否存在幻觉。\n\n{format_instructions}\n\n参考上下文:\n{context}\n\n生成的应答内容:\n{generation}",
        input_variables=["context", "generation"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser
    try:
        res = chain.invoke({"context": context_str, "generation": state["generation"]})
        logger.info(f"幻觉状态检验结果: 是否存在幻觉={res.is_hallucination}")
        return {"is_hallucination": res.is_hallucination}
    except Exception as e:
        logger.warning(f"幻觉检查解析异常，为保障安全，默认判定存在幻觉: {str(e)}")
        return {"is_hallucination": True}


def fallback_answer(state: AgentState):
    """节点：降级兜底应答通道"""
    logger.info("[节点触发] 达到最大改写重试上限或相关性彻底失效，执行安全降级兜底应答")
    return {
        "generation": "抱歉，在专属知识库中未能检索到与该问题相关的确定性权威事实，为了保证准确性，我无法回答该问题。"
    }


# =====================================================================
# 3. 确定性条件路由逻辑 (Conditional Edges)
# =====================================================================


def route_query_decision(state: AgentState) -> Literal["retrieve", "direct_answer"]:
    return "retrieve" if state["needs_retrieval"] else "direct_answer"


def route_relevance_decision(
    state: AgentState,
) -> Literal["generate_answer", "rewrite_query"]:
    return "generate_answer" if state["is_relevant"] else "rewrite_query"


def route_retry_decision(state: AgentState) -> Literal["retrieve", "fallback_answer"]:
    return "retrieve" if state["retry_count"] < 3 else "fallback_answer"


# =====================================================================
# 4. 编排并编译 LangGraph 状态图
# =====================================================================

workflow = StateGraph(AgentState)

workflow.add_node("analyze_query", analyze_query)
workflow.add_node("direct_answer", direct_answer)
workflow.add_node("retrieve", retrieve)
workflow.add_node("rerank", rerank)  # 🆕 注册新重排节点
workflow.add_node("check_relevance", check_relevance)
workflow.add_node("rewrite_query", rewrite_query)
workflow.add_node("generate_answer", generate_answer)
workflow.add_node("check_hallucination", check_hallucination)
workflow.add_node("fallback_answer", fallback_answer)

workflow.set_entry_point("analyze_query")
workflow.add_conditional_edges("analyze_query", route_query_decision)
workflow.add_edge("direct_answer", END)
# workflow.add_edge("retrieve", "check_relevance")

workflow.add_edge("retrieve", "rerank")  # retrieve 之后必须经过 rerank
workflow.add_edge("rerank", "check_relevance")  # 原retrieve之后的逻辑

workflow.add_conditional_edges("check_relevance", route_relevance_decision)
workflow.add_conditional_edges("rewrite_query", route_retry_decision)
workflow.add_edge("generate_answer", "check_hallucination")
workflow.add_edge("check_hallucination", END)
workflow.add_edge("fallback_answer", END)

app = workflow.compile()
