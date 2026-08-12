# agent_related_project

本仓库是一个 **AI Agent 相关项目合集**，汇集了多个围绕大语言模型（LLM）智能体构建的演示与工程实践，涵盖 RAG 问答、自主代码修复、智能客服、深度研究、企业级 Agent 平台、Agent 自进化、MCP 工具中台以及 Text-to-SQL 等方向。

## 项目列表

### 1. agentic_rag_knowledge_assistant_v3
基于 **LangGraph + 通义千问（Qwen）** 的 Agentic RAG 知识库问答助手。
- 意图条件路由：检索增强问答 / 闲聊分流。
- 检索链路：Milvus 向量库粗筛（k=10）→ bge-reranker 神经网络精排取 Top 3 → Qwen 生成回复。
- 内置幻觉检查与确定性状态图。
- 配套自动化评测流水线（Ragas 指标断言 + retrieve/rerank 过程评估），支撑"评测—报警—调优"闭环。

### 2. autonomous_repair_loop_agent
**自主代码修复循环 Agent（Autonomous Repair Loop）**。
- 输入：有 Bug 的代码 + 单元测试用例。
- 流程：安全沙箱隔离执行测试 → 失败则由 Qwen 诊断并生成修复代码 → 再次验证，循环直至通过。
- 可观测性：集成 LangFuse 采集耗时、Token 消耗与节点状态，并对 LLM SDK 版本差异做兼容封装。
- 提供 `main.py`（单任务调试）与 `eval_runner.py`（批量 Benchmark，如 HumanEval/MBPP）两类入口，配套 Ragas 评测引擎。

### 3. customer_service_agent
面向电商/订单场景的 **LangGraph 智能客服 Agent**。
- 多轮对话 + Checkpointing 状态管理（MemorySaver / 持久化 SqliteSaver）。
- 业务节点：意图识别（Qwen3.6-flash 强类型结构化）、订单查询、退款、用户画像推荐。
- 关键工程特性：**高额退款触发 Human-in-the-Loop 熔断阻断**，需人工审批后恢复运行（FastAPI 审批 API）。
- 提供 1000 量级订单/用户 Mock 数据与 50 大高频场景压测矩阵。

### 4. deep_research_agent_v3
**多 Agent 协作的深度研究报告生成系统**。
- 五个分工 Agent：Research Planner（规划/分类路由）、Web Searcher（多源检索）、Document Analyzer（提炼/引用）、Report Writer（撰写 2000+ 字报告）、Quality Reviewer（质量审核与反馈闭环）。
- 多源检索：Tavily（全球网页）、arXiv（学术论文）、GitHub（开源代码）、博查（国内社区/公众号）。
- 工程特性：Tool 注册表动态自省、领域意图路由（Tech/Philosophy/Business 专属 Prompt）、质量评分未达阈值自动迭代。
- 前端：Streamlit 控制台 + SQLite checkpoints 实现**断点续传/故障恢复**；后端接入 LangFuse 链路追踪。

### 5. enterprise-agent-platform
**企业级 Agent 平台（微服务 / 模块化分层架构）**。
- 架构：Streamlit 前端 → FastAPI 多租户网关（鉴权/限流/日志）→ LangGraph 编排引擎（qwen3.7-plus）→ Harness 控制层（Schema 校验/沙箱/自愈重试）→ MCP Server 集群。
- 核心能力：将前端/API 提交的 **JSON DSL 动态编译为 LangGraph 工作流**；标准 MCP Tool 注册与调用。
- 基础设施：Docker Compose 编排 PostgreSQL / Redis / Milvus / LangFuse / Prometheus；Locust 压测验证 100 并发下 P95 < 5s。

### 6. hermes_agent_system_demo
**Hermes 风格的 Agent 自进化系统（Dynamic Skill Self-Evolution）**。
- 核心理念：通过 `/learn` 机制，将 Markdown / OpenAPI 文档交给 Qwen 自动编译为 Python 工具代码，并**零停机热加载**进运行中的进程。
- 架构：Skill 标准接口（agentskills.io 思想）+ SkillManager 注册/持久化 + ReAct 执行引擎。
- 价值：突破 Prompt 窗口限制、能力运行时自积累、调用失败可自我纠错并沉淀为 `.py` 技能库，无需重启服务即可学会新 API。

### 7. personal_mcp_assistan
基于 **Anthropic MCP 协议**的"有状态、低耦合"个人 AI 助理中台（FastMCP Server）。
- 工具（Tools）：天气查询、新闻搜索、安全表达式计算、日程管理、SQLite 查询执行。
- 资源（Resources）：Northwind 数据库 Schema 结构（`schema://tables`）。
- 提示词（Prompts）：内置商业分析模板（如 `/sales_report`）。
- 设计亮点：将大批量计算与状态保留在本地 Server，仅向模型返回高价值结论，**守护上下文窗口**；一次编写、跨模型复用（适配 Claude / GPT-4o 等）。

### 8. text_to_sql
轻量级 **Text-to-SQL 自然语言转 SQL 工具**。
- 核心链路：Schema 提取 → LLM 交互生成 SQL → 在 SQLite 中执行并返回结果。
- 内置示例数据库 `chinook.db`，`main.py` 覆盖 8 个测试用例验证端到端效果。
- 适合作为"用自然语言查数据库"能力的快速原型与教学示例。

---

> 各子目录均自带独立的 `readme.md` / `README.md`，包含详细的架构图、执行流程与排障说明，可进入对应目录查阅。
