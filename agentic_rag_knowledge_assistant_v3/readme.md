# 一、目录结构
```
agentic_rag_knowledge_assistant_v3/   
│
├── data # 用来存放评测数据（json数据）、相关文档（md文件），以及评测报告（json数据）。
├── requirements.txt     # 定义显式依赖版本。
├── config.py            # 基础日志、环境变量与 Qwen 大模型统一底座。
├── vector_store.py      # 文档解析流与向量库+ES生命周期管理。
├── agent_workflow.py    # LangGraph 确定性图状态、条件路由节点及幻觉检查硬编码实现。
├── ragas_evaluate.py    # 拉取 Ragas 评测并自动断言核心指标是否达标，真实运行需要更改数据集。
├── process_evaluate.py  # 评估整个流程，特别是retrieve和rerank过程。
├── download_industrial_data.py # 临时的数据下载，已丢用。
├── download_industrial_data_v1 # 真实的评测数据下载，以及与query相关的文档，也包括噪声。
```
# 二、执行流程
## 1.流程图

```mermaid
graph TD
    %% 节点定义
    Start([用户输入 Query]) --> Router{意图条件路由}
    
    %% 路由分流
    Router -- 1. 触发知识检索 --> Node_Retrieve[retrieve 节点]
    Router -- 2. 直接闲聊回复 --> Node_Chat[direct_chat 节点]

    %% Milvus 粗筛阶段
    subgraph "向量粗筛阶段 (vector_store.py)"
        Node_Retrieve --> Milvus_DB[(WSL2 Milvus Docker)]
        Milvus_DB -->|高速向量召回 k=10| State_Raw[写入状态: raw_documents]
    end

    %% Xinference 重排阶段
    subgraph "神经网络精筛阶段 (agent_workflow.py)"
        State_Raw --> Node_Rerank[rerank 节点]
        Node_Rerank -->|HTTP POST /v1/rerank| Reranker_Model[bge-reranker-base 模型]
        Reranker_Model -->|计算语义相关度得分| Reranker_Sort[按分数从高到低重排]
        Reranker_Sort -->|截取最精准的 Top 3| State_Final[写入状态: documents]
    end

    %% 大模型生成阶段
    subgraph "大模型推理阶段 (config.py / agent_workflow.py)"
        State_Final --> Node_Generate[generate 节点]
        Node_Chat --> Node_Generate
        Node_Generate --> Qwen_LLM[Qwen 本地/大模型底座]
        Qwen_LLM -->|产生最终回复| State_Output[写入状态: generation]
    end

    %% 自动化评测闭环
    subgraph "自动化评测流水线 (evaluate.py)"
        State_Output --> Invoke_App[app.invoke 自动化收集结果]
        Invoke_App --> Ragas_Eval[Ragas 评测指标计算]
        Ragas_Eval --> Assert_Pass{指标是否达标?}
        Assert_Pass -- Yes --> Deploy[🎉 流程安全通过]
        Assert_Pass -- No --> Refine[❌ 报警并调整 Prompt/分块]
    end

    %% 样式美化（修复了旧版 VS Code 无法识别的部分颜色简写）
    style Router fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Milvus_DB fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style Reranker_Model fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    style Qwen_LLM fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style Assert_Pass fill:#ffebee,stroke:#c62828,stroke-width:2px
```

# 三、其他
milvus访问：http://localhost:8010/
