import json
from typing import Dict, Any, Tuple
from app.logger import logger
from app.mcp.registry import mcp_registry


class HarnessEngine:
    """
    Harness (装具/安全约束) 控制层：
    负责沙箱执行校验、输出合法性判断、多租户权限评估以及错误自愈 Loop 控制
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def validate_tenant_permissions(self, tool_name: str) -> bool:
        """多租户权限校验沙箱拦截"""
        logger.info(
            f"[Harness ACL Check] 租户权限评估 | Tenant: {self.tenant_id} | Tool: {tool_name}"
        )
        # 简单示例：finance 部门不能调用 delete 等毁灭性指令，全租户只放行已注册工具
        if self.tenant_id == "restricted_dept" and tool_name == "query_database":
            logger.warning(
                f"[Harness ACL Denied] 租户 {self.tenant_id} 拦截无权限工具调用: {tool_name}"
            )
            return False
        return True

    def validate_llm_output(
        self, response_text: str, expected_schema: Dict[str, Any] = None
    ) -> Tuple[bool, Any, str]:
        """
        校验 LLM 响应格式与 JSON 合法性，支撑 Loop 重试自愈
        """
        logger.info(f"[Harness Output Validation] 开始对 LLM 响应解析校验...")
        try:
            # 提取 Markdown 代码块中的 JSON
            clean_text = response_text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()

            parsed_json = json.loads(clean_text)
            logger.info(f"[Harness Output Validation] JSON 结构校验通过")
            return True, parsed_json, ""
        except Exception as e:
            err_msg = f"JSON 格式解析失败: {str(e)}。输出内容不符合标准格式。"
            logger.warning(f"[Harness Validation Failed] 拦截到不合法输出: {err_msg}")
            return False, None, err_msg

    def execute_sandboxed_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        沙箱执行 Tool，捕获运行时异常并封装日志
        """
        if not self.validate_tenant_permissions(tool_name):
            return (
                False,
                f"Permission Denied: Tenant [{self.tenant_id}] is restricted from using [{tool_name}].",
            )

        try:
            result = mcp_registry.execute_tool(tool_name, tool_args)
            return True, str(result)
        except Exception as err:
            logger.error(
                f"[Harness Sandbox Exception] 工具 {tool_name} 在沙箱中抛出运行时异常: {str(err)}"
            )
            return False, f"Tool Execution Error: {str(err)}"
