# SWE-bench 的评估 Harness 属于纯代码执行沙盒，不依赖也不调用任何 LLM API。
import json
import os
import subprocess

# 配置 Hugging Face 镜像站
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 1. 构造格式正确的标准 Patch
mock_prediction = {
    "instance_id": "django__django-11099",
    "model_name_or_path": "My_Code_Fix_Agent",
    "model_patch": (
        "diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py\n"
        "index 0b7194f..4f53ab1 100644\n"
        "--- a/django/contrib/auth/validators.py\n"
        "+++ a/django/contrib/auth/validators.py\n"
        "@@ -19,1 +19,1 @@\n"
        "-    regex = r'^[\\w.@+-]+$'\n"
        "+    regex = r'^[a-zA-Z0-9.@+-]+$'\n"
    ),
}

predictions_file = "predictions.jsonl"
with open(predictions_file, "w", encoding="utf-8") as f:
    f.write(json.dumps(mock_prediction) + "\n")

print("🚀 提交 Patch 至 SWE-bench Docker 沙盒环境中验证...")

# 2. 运行评估命令
cmd = [
    "python",
    "-m",
    "swebench.harness.run_evaluation",
    "--dataset_name",
    "princeton-nlp/SWE-bench_Lite",
    "--predictions_path",
    predictions_file,
    "--run_id",
    "test_run_001",
    "--max_workers",
    "1",
    "--instance_ids",
    "django__django-11099",
]

subprocess.run(cmd, check=True)
