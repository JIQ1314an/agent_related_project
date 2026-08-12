import streamlit as st
import httpx
import json
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="企业级 Agent 平台控制台", page_layout="wide")

st.title("🤖 企业级 Agent 平台 (Harness + Loop Architecture)")
st.caption("Powered by qwen3.7-plus & LangGraph Dynamic Orchestration")

# 侧边栏：多租户与 MCP 工具状态
st.sidebar.header("租户配置与鉴权")
tenant_id = st.sidebar.text_input("X-Tenant-ID (租户/部门ID)", value="finance_dept")

st.sidebar.subheader("MCP 工具注册中心列表")
try:
    res = httpx.get(
        f"{BACKEND_URL}/api/v1/mcp/tools", headers={"X-Tenant-ID": tenant_id}
    )
    if res.status_code == 200:
        tools = res.json()
        for t in tools:
            st.sidebar.markdown(f"**`{t['name']}`**: {t['description']}")
    else:
        st.sidebar.error("MCP 工具拉取失败")
except Exception as e:
    st.sidebar.warning(f"后端未就绪: {str(e)}")

# 主界面：动态 Workflow 组装器与测试
col1, col2 = st.columns([1, 1])

default_config = {
    "system_prompt": "你是一个严谨的企业财务助手。回答用户问题前，必须调用 search_documents 或 query_database。必须按照给定 JSON 输出格式进行响应，禁止输出多余废话。",
    "allowed_tools": ["search_documents", "query_database", "send_email"],
}

with col1:
    st.subheader("1. 动态工作流构建器 (JSON DSL)")
    config_str = st.text_area(
        "JSON 编排配置",
        value=json.dumps(default_config, ensure_ascii=False, indent=2),
        height=250,
    )
    user_input = st.text_area(
        "用户 Prompt 输入", value="帮我查一下企业出差报销的标准是怎样的？", height=100
    )
    max_loops = st.slider("Harness 最大自愈重试次数 (Max Loops)", 1, 10, 3)

    run_btn = st.button("运行 Agent 工作流", type="primary")

with col2:
    st.subheader("2. 执行结果与 Trace 控制台")
    if run_btn:
        try:
            parsed_config = json.loads(config_str)
            payload = {
                "workflow_config": parsed_config,
                "user_input": user_input,
                "max_loops": max_loops,
            }

            with st.spinner("LangGraph + Harness 闭环执行中..."):
                headers = {"X-Tenant-ID": tenant_id}
                response = httpx.post(
                    f"{BACKEND_URL}/api/v1/workflow/run",
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success("工作流执行完结！")
                    st.json(result)
                else:
                    st.error(f"执行失败 [HTTP {response.status_code}]: {response.text}")
        except json.JSONDecodeError:
            st.error("JSON 配置文件格式错误，请检查 syntax！")
        except Exception as ex:
            st.error(f"请求异常: {str(ex)}")
