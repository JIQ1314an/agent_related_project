import time
from typing import Dict, Any, List
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from app.config import settings
from app.logger import logger
from app.mcp.registry import mcp_registry
from app.orchestrator.builder import WorkflowCompiler

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="企业级 Agent 平台 + Harness/Loop 控制引擎 API 网关",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局审计与监控中间件
@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    start_time = time.time()
    tenant_id = request.headers.get("X-Tenant-ID", "anonymous")
    logger.info(
        f"[API Request Start] Path: {request.url.path} | Method: {request.method} | Tenant: {tenant_id}"
    )

    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"[API Request End] Path: {request.url.path} | Status: {response.status_code} | Duration: {process_time:.2f}ms"
        )
        return response
    except Exception as e:
        logger.error(f"[API Unhandled Exception] Error: {str(e)}", exc_info=True)
        raise e


# --- 请求与响应 Schema 定义 ---
class WorkflowRunRequest(BaseModel):
    workflow_config: Dict[str, Any] = Field(
        ...,
        example={
            "system_prompt": "你是一个资深的财务智能助手，必须调用 search_documents 或 query_database 来回答问题，最终回答以 JSON 格式输出。",
            "allowed_tools": ["search_documents", "query_database"],
        },
    )
    user_input: str = Field(..., example="帮我检索下差旅报销的标准是怎样的？")
    max_loops: int = Field(3, ge=1, le=10)


class WorkflowRunResponse(BaseModel):
    status: str
    tenant_id: str
    final_output: str
    total_loops: int


# --- API 端点 ---
@app.get("/health")
def health_check():
    return {"status": "healthy", "model": settings.QWEN_MODEL_NAME}


@app.get("/api/v1/mcp/tools", response_model=List[Dict[str, Any]])
def list_mcp_tools(x_tenant_id: str = Header(default="default_tenant")):
    """获取所有已注册的 MCP 工具列表示例"""
    logger.info(f"[MCP API] 租户 {x_tenant_id} 查询工具清单")
    return mcp_registry.list_tools()


@app.post("/api/v1/workflow/run", response_model=WorkflowRunResponse)
async def run_agent_workflow(
    req: WorkflowRunRequest,
    x_tenant_id: str = Header(default="default_tenant", alias="X-Tenant-ID"),
):
    """
    接收 JSON 组装的动态工作流配置，编译并由 Harness 托管执行 LangGraph Loop
    """
    logger.info(
        f"[Workflow Request] 收到工作流触发任务 | 租户: {x_tenant_id} | 输入: {req.user_input}"
    )

    try:
        # 1. 动态编译 StateGraph
        compiler = WorkflowCompiler(req.workflow_config)
        graph = compiler.build()

        # 2. 构造初始 State
        initial_state = {
            "messages": [HumanMessage(content=req.user_input)],
            "tenant_id": x_tenant_id,
            "current_loop": 0,
            "max_loops": req.max_loops,
            "validation_error": "",
            "execution_result": "",
            "is_completed": False,
        }

        # 3. 执行 LangGraph 图
        final_state = graph.invoke(initial_state)

        logger.info(
            f"[Workflow Complete] 执行完毕 | 最终 Loop 轮次: {final_state.get('current_loop')}"
        )

        return WorkflowRunResponse(
            status="SUCCESS",
            tenant_id=x_tenant_id,
            final_output=final_state.get("execution_result", "无明确输出"),
            total_loops=final_state.get("current_loop", 0),
        )

    except Exception as err:
        logger.error(
            f"[Workflow Fatal Error] 执行过程抛出异常: {str(err)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Agent Workflow Internal Error: {str(err)}"
        )
