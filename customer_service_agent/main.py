from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from src.graph import compiled_app
from src.logger import agent_logger

app = FastAPI(title="Production-Grade Workflow Agent API", version="1.0.0")


class ChatPayload(BaseModel):
    session_id: str
    message: str


class ReviewPayload(BaseModel):
    session_id: str
    approved: bool


@app.post("/api/v1/chat")
async def chat_endpoint(payload: ChatPayload):
    """大模型核心会话与工作流网关"""
    config = {"configurable": {"thread_id": payload.session_id}}
    input_state = {"messages": [HumanMessage(content=payload.message)]}

    try:
        agent_logger.info(
            f"接收到会话请求. Session: {payload.session_id} | 消息: {payload.message}"
        )
        output_state = compiled_app.invoke(input_state, config=config)
        state_info = compiled_app.get_state(config)

        # 拦截：判断状态机当前是否被 interrupt 机制挂起（等待大额资产人工审批）
        if (
            state_info.next
            and len(state_info.tasks) > 0
            and state_info.tasks[0].interrupts
        ):
            interrupt_detail = state_info.tasks[0].interrupts[0].value
            return {
                "status": "INTERRUPTED_AWAITING_REVIEW",
                "session_id": payload.session_id,
                "review_details": interrupt_detail,
                "response": "您的请求涉及敏感或大额资产变动，系统已触发人工安全策略介入审核，请耐心等待。",
            }

        latest_msg = output_state["messages"][-1].content
        return {
            "status": "SUCCESS",
            "session_id": payload.session_id,
            "response": latest_msg,
        }

    except Exception as e:
        agent_logger.error(f"网关处理发生内部错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/refund/review")
async def review_endpoint(payload: ReviewPayload):
    """
    提供给风控后台人工审核调用的入口API。通过传入相同 session_id 注入人工决策指令，使挂起的状态机继续向后运行
    """
    config = {"configurable": {"thread_id": payload.session_id}}

    try:
        state_info = compiled_app.get_state(config)
        if not state_info.next:
            raise HTTPException(
                status_code=400, detail="该会话当前未处于被阻断的审核流程中。"
            )

        agent_logger.info(
            f"人工审核操作介入。会话: {payload.session_id} | 审核结果: {payload.approved}"
        )

        # 封装 Command 指令对象，给当前挂起节点传入注入值并强制 Resume 状态机
        resume_command = Command(resume={"approved": payload.approved})
        output_name = compiled_app.invoke(resume_command, config=config)

        latest_msg = output_name["messages"][-1].content
        return {
            "status": "RESUMED_SUCCESS",
            "session_id": payload.session_id,
            "response": latest_msg,
        }
    except Exception as e:
        agent_logger.error(f"审批恢复失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # 工业级高并发 ASGI 引擎拉起服务 # 文件名：服务名
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
