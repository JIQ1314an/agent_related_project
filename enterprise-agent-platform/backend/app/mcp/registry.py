import json
from typing import Dict, Any, Callable, List
from app.logger import logger


class MCPRegistry:
    """
    MCP (Model Context Protocol) 工具注册中心
    管理 Agent 可调用的底层系统 API（数据库查询、文档检索、邮件发送等）
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register_tool(
        self, name: str, description: str, func: Callable, schema: Dict[str, Any]
    ):
        """注册一个新的 Tool 节点"""
        self._tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "parameters": schema,
        }
        logger.info(f"[MCP Registry] 工具注册成功: {name}")

    def get_tool(self, name: str) -> Dict[str, Any]:
        if name not in self._tools:
            raise KeyError(f"未找到该 Tool: {name}")
        return self._tools[name]

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": v["name"],
                "description": v["description"],
                "parameters": v["parameters"],
            }
            for k, v in self._tools.items()
        ]

    def execute_tool(self, name: str, kwargs: Dict[str, Any]) -> Any:
        """安全地执行 MCP 注册工具"""
        tool = self.get_tool(name)
        logger.info(
            f"[MCP Execution] 启动工具执行 | 工具: {name} | 参数: {json.dumps(kwargs, ensure_ascii=False)}"
        )
        try:
            result = tool["func"](**kwargs)
            logger.info(f"[MCP Execution] 工具执行成功 | 工具: {name} | 结果: {result}")
            return result
        except Exception as e:
            logger.error(
                f"[MCP Execution Exception] 工具执行失败 | 工具: {name} | 错误: {str(e)}",
                exc_info=True,
            )
            raise e

    def _register_default_tools(self):
        """内置生产常用的默认示例 Tool"""

        def query_database(sql_query: str) -> str:
            # 模拟 PostgreSQL 查询
            return f"Query Result for [{sql_query}]: [{'id': 101, 'status': 'ACTIVE', 'balance': 50000}]"

        def search_documents(query: str) -> str:
            # 模拟向量数据库检索
            return f"Retrieved Context for [{query}]: 企业出差报销规程：上限 800 元/天，需提供增值税发票。"

        def send_email(recipient: str, subject: str, content: str) -> str:
            # 模拟邮件 API 发送
            return f"SUCCESS: Email sent to {recipient} with subject '{subject}'"

        self.register_tool(
            "query_database",
            "查询企业数据库SQL指令",
            query_database,
            {
                "type": "object",
                "properties": {"sql_query": {"type": "string"}},
                "required": ["sql_query"],
            },
        )
        self.register_tool(
            "search_documents",
            "检索知识库与企业文档",
            search_documents,
            {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )
        self.register_tool(
            "send_email",
            "发送企业公文或通知邮件",
            send_email,
            {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string"},
                    "subject": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["recipient", "subject", "content"],
            },
        )


mcp_registry = MCPRegistry()
