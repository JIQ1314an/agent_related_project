from locust import HttpUser, task, between
import json


class AgentPlatformUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def test_workflow_execution(self):
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": "stress_test_tenant",
        }
        payload = {
            "workflow_config": {
                "system_prompt": "你是一个快速响应系统，必须使用 search_documents，并以 JSON 格式输出结果。",
                "allowed_tools": ["search_documents"],
            },
            "user_input": "高并发压力测试请求",
            "max_loops": 2,
        }
        with self.client.post(
            "/api/v1/workflow/run",
            data=json.dumps(payload),
            headers=headers,
            catch_response=True,
        ) as response:
            if (
                response.status_code == 200
                and response.json().get("status") == "SUCCESS"
            ):
                response.success()
            else:
                response.failure(
                    f"Request Failed: status={response.status_code}, body={response.text}"
                )
