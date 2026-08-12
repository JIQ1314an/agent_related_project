import os

WorkspaceId = "llm-4wyxwbawaegb4be8"  # 替换为你的阿里云工作空间ID
qwen_api_key = os.environ.get("DASHSCOPE_API_KEY")
qwen_base_url = f"https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"  # 关键点：切换为阿里云的 OpenAI 兼容端点

model_name = "qwen3.6-flash"  # 或者 deepseek-chat
