# 一、架构与核心工程设计
系统采用微服务与模块化分层架构：
```

                    ┌─────────────────────────┐
                    │    Streamlit 前端 UI    │
                    └────────────┬────────────┘
                                 │ HTTP / REST
                    ┌────────────▼────────────┐
                    │     FastAPI Gateway     │
                    │ (多租户/鉴权/限流/日志)  │
                    └────────────┬────────────┘
                                 │ Dynamic State Graph
                    ┌────────────▼────────────┐
                    │  LangGraph 编排引擎     │ <── Model: qwen3.7-plus
                    └────────────┬────────────┘
                                 │ Tool Protocol JSON-RPC
                    ┌────────────▼────────────┐
                    │      Harness 控制层     │
                    │ ┌─────────────────────┐ │
                    │ │  输入/输出 Schema 校验 │ │
                    │ │  沙箱隔离与权限评估 │ │
                    │ │  Loop 自主修正/重试  │ │
                    │ └─────────────────────┘ │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     MCP Server 集群     │
                    │ (DB / RAG / Email/ API) │
                    └─────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  PostgreSQL  │         │    Redis     │         │ LangFuse/Prom│
│ (配置/审计)  │         │ (状态与缓存) │         │  (可观测层)  │
└──────────────┘         └──────────────┘         └──────────────┘
```

# 二、项目工程实施流程
## ① 容器化基础设施编排
Docker Compose 基础服务栈部署  

初始化 PostgreSQL、Redis、Milvus、LangFuse 与 Prometheus 基础组件，确保数据持久化、租户缓存以及全链路 OpenTelemetry 追踪接入。


## ② 核心后端 Harness 与 Loop 控制引擎开发
构建保障的重试与沙箱验层

实现 Harness 控制层，接管所有 Tool 调用与 LLM 响应解析。包含 JSON Schema 结构化输出强校验、自愈重试逻辑（Loop Retry）、敏感操作权限检测以及安全沙箱执行。

## ③ LangGraph 动态工作流编译引擎构建
JSON DSL 转换为 StateGraph

编写工作流编译器，将前端或 API 提交的 JSON 配置动态编译为包含 LLM Node -> Validation Node -> Harness Tool Node -> Loop Decision Edge 的 LangGraph 

## ④ FastAPI API 网关与 MCP 注册中心整合
多租户隔离与全链路日志记录

构建带 X-Tenant-ID 请求头校验的多租户 API Gateway，接入 LangFuse SDK 实现 LLM 调用 Trace 采集，并暴露标准的 MCP Tool 注册与调用接口。


## ⑤ Streamlit 可视化控制台与高并发压测
前端交互与 100 并发性能验收

构建 Streamlit 前端，提供 JSON Workflow 编辑器、运行调试日志面板与 Trace 链接跳转；编写 Locust 压力测试脚本验证 100 并发下 P95 < 5s 的性能目标。

三、项目代码结构目录
```
enterprise-agent-platform/
├── .env
├── docker-compose.yml
├── prometheus.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py          (FastAPI Gateway, 多租户中间件)
│       ├── config.py         (配置管理)
│       ├── logger.py         (结构化日志)
│       ├── harness/
│       │   ├── __init__.py
│       │   └── engine.py     (沙箱执行/重试逻辑/JSON Schema校验)
│       ├── mcp/
│       │   ├── __init__.py
│       │   └── registry.py   (MCP工具注册中心)
│       └── orchestrator/
│           ├── __init__.py
│           └── builder.py    (JSON DSL → LangGraph StateGraph编译)
└── frontend/
    ├── Dockerfile
    └── app.py                (Streamlit可视化控制台)
```