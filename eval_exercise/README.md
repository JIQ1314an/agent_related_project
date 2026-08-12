这四个框架之所以让人困惑，是因为它们**并非同一类工具**。它们被分为两大阵营：**Ragas & DeepEval** 属于“应用层单元测试与 RAG 评估工具”（测你自己的业务应用）；**SWE-bench & Inspect AI** 属于“基准与通用 Agent 评估平台”（测模型或 Agent 的综合能力底座）。

---

### 一、 核心分类与对比汇总

| 框架 | 核心类别 | 评测什么 | 评测机制 (How) | 如何嵌入你的代码 (Where) |
| --- | --- | --- | --- | --- |
| **Ragas** | RAG 专项评估 | 检索召回率、回答忠实度、上下文相关性 | LLM-as-a-Judge（对比 Input/Context/Output） | 离线评估脚本，批量分析 RAG pipeline 输出 |
| **DeepEval** | 业务单元测试 | 幻觉、毒性、输出格式、自定义 G-Eval | 类似 `pytest` 断言 + 多维度 LLM 裁判 | CI/CD 自动化测试流程（如 GitHub Actions） |
| **SWE-bench** | 编程 Agent 基准 | Agent 解决真实 GitHub Issue/Bug 的能力 | 在 **Docker 沙盒** 中运行真实项目的 `pytest` | 作为独立基准环境，将你的 Agent 接入其评测 Harness |
| **Inspect AI** | 通用 Agent 评估平台 | 模型与 Agent 的安全、推理、工具调用、CTF 等 | 模块化 (`Dataset` $\rightarrow$ `Solver` $\rightarrow$ `Scorer`) + 沙盒 | CLI/命令行评估，在模型上线前跑安全/能力测试 |

---

### 二、 逐一拆解：各框架如何运行与嵌入

#### 1. Ragas：RAG 系统的“质量放大镜”

* **评测什么**：专攻 **RAG（检索增强生成）** 架构的四大核心指标：忠实度（Faithfulness，有无幻觉）、答案相关性、上下文精准度、上下文召回率。
* **如何评测**：采用 **LLM-as-a-Judge** 模式。你不需要准备标准答案（Ground Truth）也能测幻觉。它让 GPT-4 拿着检索出的 `Context` 和生成的 `Answer` 进行对比推理。
* **如何嵌入**：**业务日志回溯 / 离线脚本**。
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

# 1. 收集你的 RAG 系统运行出来的日志数据
dataset = Dataset.from_dict({
    "question": ["如何配置 Langfuse？"],
    "contexts": [["Langfuse 需要配置 PUBLIC_KEY 和 SECRET_KEY..."]],
    "answer": ["你需要配置 LANGFUSE_PUBLIC_KEY..."],
})

# 2. 调用 Ragas 评测并输出分数
results = evaluate(dataset, metrics=[faithfulness, answer_relevancy])

```



---

#### 2. DeepEval：LLM 应用的“Pytest”

* **评测什么**：LLM 输出质量的**单元测试**。包含幻觉测试、G-Eval（用自然语言定义评估标准，如“是否包含礼貌用语”）、安全性/毒性测试等。
* **如何评测**：用 `assert_test()` 断言方式。结合预置指标或 G-Eval，由后台大模型判断分数是否大于设定的阈值（阈值如 0.7）。
* **如何嵌入**：**项目单元测试目录（CI/CD）**。直接写在项目的 `tests/test_llm.py` 中。
```python
from deepeval import assert_test
from deepeval.metrics import HallucinationMetric
from deepeval.test_case import LLMTestCase


def test_agent_hallucination():
    # 构造业务测试用例
    test_case = LLMTestCase(
        input="用户问：我的订单到了吗？",
        actual_output="您的订单已发货，快递单号为 12345",
        context=["用户订单状态为：处理中，尚未发货"],  # 实际上下文
    )
    metric = HallucinationMetric(threshold=0.5)
    # 像普通 pytest 一样断言，不通过则 CI 构建失败
    assert_test(test_case, [metric])

```



---

#### 3. SWE-bench：代码 Agent 的“高考考场”

* **评测什么**：评估 AI Agent 解决**真实世界软件工程问题**的能力（如修复 Django、SymPy 等知名开源库的真实 GitHub Issue）。
* **如何评测**：**客观的测试用例通关率（PASS/FAIL）**。
1. 给 Agent 一个 GitHub Issue 描述和代码库。
2. Agent 思考并修改代码，输出一个 `.patch`（git diff 补丁文件）。
3. SWE-bench 将补丁应用到 **Docker 隔离容器** 中，并自动运行项目已有的真实 `pytest` / `unittest`。测试全部 PASS 则算解决。


* **如何嵌入**：**外挂评测套件（Evaluation Harness）**。它不是库，而是一个独立的基准运行器。
```bash
# 你的 Agent 接口对接 SWE-bench 提供的 Runner
python -m swebench.harness.run_evaluation \
    --dataset_name principal-ai/SWE-bench_Lite \
    --predictions_path ./my_agent_patches.jsonl \
    --max_workers 4

```



---

#### 4. Inspect AI：通用 Agent / 模型能力的“测试床”

* **评测什么**：英国 AI 安全局（UK AISI）开源的**通用大模型与 Agent 测评工具**。支持评测网络安全攻防（CTF）、复杂逻辑推理、Tool Use 各种能力。
* **如何评测**：三层解耦架构：
* **Dataset**：评估题目/任务（如 100 道密码破译题）。
* **Solver**：你的 Agent 策略（如 ReAct Agent、Direct Prompt）。
* **Scorer**：打分器（支持基于正则表达式匹配、代码执行、或 LLM 判定）。


* **如何嵌入**：**独立的 Evaluator 架构（CLI 命令行）**。
```python
from inspect_ai import Task, task
from inspect_ai.dataset import example_dataset
from inspect_ai.scorer import model_graded_fact


@task
def ctf_challenge():
    return Task(
        dataset=example_dataset("ctf_tasks"),
        plan=my_agent_solver(),  # 接入你的 Agent 逻辑
        scorer=model_graded_fact(),  # 评测打分
    )

```


在终端直接运行命令行调用：`inspect eval ctf_task.py --model openai/gpt-4o`。

---

### 三、 总结：如何为你的项目选择？

* 做 **RAG 搜索问答系统** $\rightarrow$ 选 **Ragas**（专门衡量检索与生成质量）。
* 防止 **LLM 迭代过程中能力退化，想在 GitHub Actions 中自动把关** $\rightarrow$ 选 **DeepEval**。
* 开发了一个 **Autonomous Coding Agent（自主写代码 Agent）** 想向业界证明能力 $\rightarrow$ 跑 **SWE-bench**。
* 评估 **Agent 的安全性、工具调用能力或自研模型的综合水平** $\rightarrow$ 用 **Inspect AI** 构建评测集。

========================================================================================

这四个实战项目涵盖了各个框架的核心机制、适用场景和关键代码，帮助你快速入手。

---

### 项目 1：基于 Ragas 的企业知识库 RAG 效果离线诊断

**适用场景**：你开发了一个基于 LangChain/LlamaIndex 的 RAG 问答机器人，上线前或迭代索引时，需要批量评估回答是否有幻觉、检索出来的文档准不准。

**架构位置**：**离线评估脚本**。在 RAG pipeline 执行完后，收集输出的 log/json，批量投给 Ragas 分析。

#### 核心代码实现 (`eval_ragas.py`)

```python
import os
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,  # 答案相关性
    context_precision,  # 上下文精准度
    context_recall,  # 上下文召回率
    faithfulness,  # 忠实度（防幻觉）
)

# 1. 模拟你的 RAG 系统检索和生成的结果日志
eval_data = {
    "question": ["Langfuse 的 API Key 如何配置？", "Python 如何读取环境变量？"],
    "contexts": [
        ["需要在 .env 中配置 LANGFUSE_PUBLIC_KEY 和 LANGFUSE_SECRET_KEY。"],
        ["使用 os.getenv('KEY_NAME') 或 os.environ['KEY_NAME'] 读取。"],
    ],
    "answer": [
        "你需要设置 LANGFUSE_PUBLIC_KEY 和 LANGFUSE_SECRET_KEY 环境变量。",
        "可以通过 import os 之后调用 os.getenv() 获取。",
    ],
    "ground_truth": [  # 可选：没有标准答案时，Ragas 也可评估 faithfulness 和 answer_relevancy
        "在环境变量中添加 LANGFUSE_PUBLIC_KEY 与 LANGFUSE_SECRET_KEY。",
        "使用 import os; os.getenv('VAR')。",
    ],
}

dataset = Dataset.from_dict(eval_data)

# 2. 执行评估（背后会调用 OpenAI/指定 LLM 作为裁判）
results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
)

# 3. 查看各指标得分 (0 ~ 1)
df = results.to_pandas()
print(df[["faithfulness", "answer_relevancy", "context_precision"]])

```

* **项目体验收获**：理解 Ragas 的核心——**不需要对每个问题手写正则断言**，它通过拆解 Context 和 Answer 句子的语义蕴含关系（Entailment）来客观打分。

---

### 项目 2：基于 DeepEval 的客服 Agent CI/CD 自动化回归测试

**适用场景**：客服 Agent 经常更新 Prompt，你希望每次向 GitHub 提交代码（PR）时，自动运行一套“单元测试”，防止修改 Prompt 导致 Agent 产生幻觉或胡言乱语。

**架构位置**：**项目的 `tests/` 目录**，直接接入 `pytest` 命令，并在 CI/CD (GitHub Actions) 中拦截不合格代码。

#### 核心代码实现 (`tests/test_agent.py`)

```python
import pytest
from deepeval import assert_test
from deepeval.metrics import GEval, HallucinationMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

# 模拟你的 Agent 函数
def my_customer_agent(user_input: str) -> str:
    # 模拟 Agent 输出
    return "您的订单 123456 已经发货，预计明天送达。"


def test_order_status_hallucination():
    # 1. 构造测试用例与检索到的上下文
    context = ["订单 123456 当前状态：仓库打包中，尚未交付快递。"]
    user_input = "我的订单 123456 发货了吗？"
    actual_output = my_customer_agent(user_input)

    test_case = LLMTestCase(
        input=user_input, actual_output=actual_output, context=context
    )

    # 2. 挂载防幻觉指标（阈值设为 0.5，超过阈值判定测试失败）
    hallucination_metric = HallucinationMetric(threshold=0.5)

    # 3. 挂载自定义 G-Eval 指标（用自然语言定义评估标准）
    politeness_metric = GEval(
        name="Politeness",
        criteria="评估回答是否语气礼貌且专业",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.7,
    )

    # 4. 执行 Pytest 断言
    assert_test(test_case, [hallucination_metric, politeness_metric])

```

* **运行命令**：在终端直接敲 `deepeval test run tests/test_agent.py`。
* **项目体验收获**：体验把 LLM 评估变成像传统软件工程写 `assert` 同样简单的流程。

---

### 项目 3：基于 SWE-bench Lite 的代码修补 Agent 评估 Harness

**适用场景**：你写了一个 Autonomous Coding Agent（自主写代码/修 Bug 智能体），想评估它在真实的开源项目（如 Django、sympy）上能真正解决多少 GitHub Issue。

**架构位置**：**外挂评测跑轮（Harness）**。Agent 作为一个独立的解题器（Solver），输出 `.patch` 补丁文件给 SWE-bench 在 Docker 沙盒里跑单元测试。

#### 核心流程实现 (`run_swebench_eval.py`)

```python
import json
import os

# 1. 步骤 A：让你的 Code Agent 针对 SWE-bench 的题目生成 Patch（Git Diff）
# 假设 SWE-bench 提供了一个 Issue：instance_id="django__django-11099"
mock_patch_result = {
    "instance_id": "django__django-11099",
    "model_name_or_path": "MyCustomCodingAgent",
    "model_patch": """diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py
index 0b7194f..4f53ab1 100644
--- a/django/contrib/auth/validators.py
+++ a/django/contrib/auth/validators.py
@@ -17,7 +17,7 @@ class ASCIIUsernameValidator(validators.RegexValidator):
-    regex = r'^[\w.@+-]+$'
+    regex = r'^[a-zA-Z0-9.@+-]+$'
""",
}

# 2. 步骤 B：保存预测结果为 predictions.jsonl
with open("predictions.jsonl", "w") as f:
    f.write(json.dumps(mock_patch_result) + "\n")

# 3. 步骤 C：调用 SWE-bench Harness 在 Docker 环境中跑真实测试用例
# （需要本地安装 docker 和 swebench 包）
os.system(
    "python -m swebench.harness.run_evaluation "
    "--dataset_name principal-ai/SWE-bench_Lite "
    "--predictions_path predictions.jsonl "
    "--max_workers 1"
)

```

* **项目体验收获**：明确 SWE-bench **不关心你 Agent 内部的思考过程**，它只关心在隔离沙盒里应用你的 Git Patch 后，原项目的 `pytest` 能不能全绿通过（Pass Rate）。


========================================================================
**评估过程（`run_evaluation`）本身没有任何大模型参与。**

SWE-bench 的评估 Harness 属于**纯代码执行沙盒**，不依赖也不调用任何 LLM API。

---

### 1. SWE-bench 的运行原理

整个 SWE-bench 的测试流程分为两个独立阶段：

```
[阶段一：Agent 求解阶段]  ---> 生成 predictions.jsonl (包含 Git Diff)
                                       │
                                       ▼
[阶段二：Harness 评估阶段] ---> Docker 镜像 -> git apply -> 跑 pytest/unittest -> 判定 PASS/FAIL

```

* **求解阶段（有大模型）**：写代码 Agent 读取 GitHub Issue，让 LLM 生成修改代码并导出 `git diff` 写入 `predictions.jsonl`。
* **评估阶段（无大模型）**：`run_evaluation` 拿到 `predictions.jsonl` 后，直接启动 Docker 容器，把 `git diff` 贴进仓库，然后执行该项目原生的 `pytest` 或 `unittest`。整个过程是**纯确定性的软件测试**，零 Token 消耗。

---

### 2. 如何在“生成阶段”使用千问（Qwen）？

如果你想构建一个**基于 Qwen 的 Coding Agent** 来自动解决 Issue 并生成 SWE-bench 要求的 `predictions.jsonl`，示例代码如下：

```python
import json
from langchain_openai import ChatOpenAI

# 1. 配置 Qwen 作为 Coding Agent 的基座大模型
coder_llm = ChatOpenAI(
    model="qwen3.7-plus",  # 或 qwen-coder-turbo / qwen-max
    temperature=0,
    openai_api_key="your-dashscope-api-key",
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 2. 模拟从 SWE-bench 获取的 GitHub Issue
github_issue = """
Issue: ASCIIUsernameValidator in django.contrib.auth.validators allows invalid characters.
Please provide a git diff patch to fix this regex bug.
"""

# 3. 让 Qwen 生成修复 Patch
prompt = f"你是一个 Python 专家，请根据以下 Issue 输出标准的 git diff 补丁，只输出 diff 内容：\n{github_issue}"
patch_response = coder_llm.invoke(prompt).content

# 4. 导出为 SWE-bench 识别的 predictions.jsonl 格式
prediction = {
    "instance_id": "django__django-11099",
    "model_name_or_path": "qwen3.7-plus-agent",
    "model_patch": patch_response,
}

with open("predictions.jsonl", "w", encoding="utf-8") as f:
    f.write(json.dumps(prediction) + "\n")

print("✅ 已由 Qwen 生成 predictions.jsonl，现在可以运行 python run_swebench_eval.py 进行 Docker 跑分测验。")

```

生成 `predictions.jsonl` 后，再运行 `python run_swebench_eval.py`，即可完成对 Qwen 代码修复能力的自动化验证。


---

### 项目 4：基于 Inspect AI 的 Tool-Calling Agent 能力与安全基准

**适用场景**：你需要测试 Agent 使用 Python 代码解释器、SQL 数据库或 Shell 工具解决复杂多步问题的能力（或安全性/CTF 攻防）。

**架构位置**：**独立的 Task / Evaluator 评测框架**。采用 `Dataset -> Solver -> Scorer` 三层解耦设计。

#### 核心代码实现 (`benchmark_task.py`)

```python
from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import match
from inspect_ai.solver import generate, use_tools
from inspect_ai.tool import python


# 1. 定义测试数据集（题目 + 标准答案）
dataset = MemoryDataset(
    samples=[
        Sample(
            input="请计算 1 到 100 中所有质数的和。",
            target="1060",  # 正确答案
        ),
        Sample(
            input="计算字符串 'hello world' 中字母 l 出现的次数乘以 15。",
            target="45",
        ),
    ]
)


# 2. 定义评估 Task
@task
def python_agent_capability():
    return Task(
        dataset=dataset,
        # Solver：为 Agent 挂载 Python 执行工具，并允许它多步思考生成
        plan=[
            use_tools(python()),  # 给 Agent 提供 Python 代码沙盒执行工具
            generate(),  # 让 Agent 循环执行 Tool 直到给出 final answer
        ],
        # Scorer：对 Agent 输出进行模式匹配/提取答案与 target 比对
        scorer=match(),
    )

```

* **运行命令**：`inspect eval benchmark_task.py --model openai/gpt-4o`。
* **项目体验收获**：感受 Inspect AI 的模块化架构，体验内置的终端交互式 Dashboard 分析 Agent 在哪一步工具调用时做出了错误决策。

===========================================================================
在 `inspect-ai` 评估框架中，将模型更换为 **Qwen（通义千问）** 主要有以下 3 种配置方式：

### 方式一：调用阿里云 DashScope API（推荐）

通过 OpenAI 兼容接口直接调用云端 Qwen 模型。

**1. 配置环境变量**

```bash
# Linux / macOS
export OPENAI_API_KEY="sk-xxx"  # 替换为你的 DashScope API Key
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-xxx"
$env:OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

```

**2. 运行评估命令**

```bash
inspect eval benchmark_task.py --model openai/qwen-max

```

*(常用模型标识：`openai/qwen-max`、`openai/qwen-plus`、`openai/qwen2.5-72b-instruct`、`openai/qwen2.5-coder-32b-instruct`)*

---

### 方式二：使用 Ollama 本地运行 Qwen

如果本地通过 Ollama 启动了 Qwen 模型（如 `ollama run qwen2.5-coder`）：

```bash
inspect eval benchmark_task.py --model ollama/qwen2.5-coder

```

---

### 方式三：使用 vLLM 私有化部署

如果使用 vLLM 在本地/服务器部署了 Qwen 模型并开启了 OpenAI 兼容服务：

**1. 配置环境变量**

```bash
export OPENAI_API_BASE="http://localhost:8000/v1"  # 你的 vLLM 服务地址
export OPENAI_API_KEY="none"

```

**2. 运行评估命令**

```bash
inspect eval benchmark_task.py --model openai/Qwen2.5-72B-Instruct

```

报错根因是 **`python_agent_capability` 任务启用了代码执行/工具调用，但未指定沙箱（Sandbox）隔离环境**。

在 Inspect AI 中，只要 Agent 需要运行 Python 代码或 Shell 命令，就必须明确指定代码执行的沙箱类型（如 `local` 本地环境或 `docker` 容器环境）。

---

### 解决方案

#### 方式一：在命令行中直接指定 `--sandbox`（推荐）

如果希望直接在**本地主机**执行代码：

```bash
inspect eval benchmark_task.py --model openai/qwen3.7-flash-2026-07-15 --sandbox local

```

如果是在 **Docker 容器**中隔离执行（需要本地已启动 Docker）：

```bash
inspect eval benchmark_task.py --model openai/qwen3.7-flash-2026-07-15 --sandbox docker

```

---

#### 方式二：在 `benchmark_task.py` 代码中配置默认沙箱

打开 `benchmark_task.py`，在 `@task` 函数返回的 `Task` 对象中添加 `sandbox` 参数：

```python
from inspect_ai import Task, task

@task
def python_agent_capability():
    return Task(
        dataset=...,
        plan=...,
        scorer=...,
        sandbox="local",  # 指定默认沙箱类型，可选 "local" 或 "docker"
    )

```

修改后，直接运行原命令即可正常启动评估。



在终端中运行 Inspect AI 内置的日志可视化工具即可在浏览器中打开评估报告：

```bash
inspect view

```

**常用启动方式与配置技巧**

* **默认启动**：直接运行 `inspect view`，会自动读取当前项目根目录下的 `logs/` 文件夹，并在默认浏览器打开 `http://localhost:7575`。
* **指定日志目录**：如果日志保存在其他位置，使用 `--log-dir` 参数：
```bash
inspect view --log-dir ./your_log_directory

```


* **远程服务器 / Docker 环境访问**：如果在远端开发机上运行，可以绑定公网/局域网 IP：
```bash
inspect view --host 0.0.0.0 --port 7575

```


在本地浏览器输入 `http://<服务器IP>:7575` 即可访问。

**可视化界面排查要点**

* **Samples 视图**：点开未通过的 Sample（例如得分 0 的题目），可以完整查看模型与沙盒环境的**多轮交互日志**、**调用的 Bash/Python 工具命令**、**沙盒标准输出（stdout/stderr）** 以及最后的评分判定逻辑。
* **Transcript 时间轴**：复盘 Agent 在每一步的思考过程（Thinking/Reasoning）和决策路径，精确定位导致最终报错或测试失败的具体步骤。
* **Info 页签**：查看本次评估的全局配置（Token 耗时、Prompt 消耗、Model 参数与 Docker 沙盒规格）。
===========================================================================
---

### 四个项目总结对比

* **想测 RAG 问答准确度与防幻觉** $\rightarrow$ 先写 **项目 1 (Ragas)**
* **想给 LLM 应用加 CI/CD 自动化拦截门禁** $\rightarrow$ 先写 **项目 2 (DeepEval)**
* **想跑代码生成/修复 Agent 行业标准分** $\rightarrow$ 尝试 **项目 3 (SWE-bench)**
* **想系统评估 Agent 工具调用/逻辑推理能力** $\rightarrow$ 使用 **项目 4 (Inspect AI)**
