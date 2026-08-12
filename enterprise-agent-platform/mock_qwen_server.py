import time
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Qwen Mock API Server")


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def mock_chat_completions(payload: dict):
    # 模拟极轻微的网络延迟 (20ms)
    time.sleep(0.02)

    # 模拟大模型返回的标准 ReAct JSON
    # 第 1 次请求模拟返回 final_answer，直接完成链路
    mock_content = '{"action": "final_answer", "result": "这是来自 Mock Qwen API 的高并发测试响应。"}'

    return {
        "id": "chatcmpl-mock-qwen-123",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "qwen3.7-plus",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": mock_content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
