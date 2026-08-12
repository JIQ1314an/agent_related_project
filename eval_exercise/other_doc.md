### 一、 什么是 SWE-bench？

**SWE-bench**（全称 Software Engineering Benchmark）是一个用于评估大语言模型（LLM）**软件工程实战能力**的权威基准测试。

* **它的核心任务**：让 AI 像人类程序员一样，去修复真实的 GitHub 开源项目中的 Bug（或者实现新功能）。
* **它的数据来源**：全部来自真实的开源项目（如 Django, SymPy, Scikit-learn 等）。每一个测试样本都包含：
1. 一个真实的 GitHub **Issue** 描述（用户遇到的问题）。
2. 发生 Bug 时的**代码库状态**（某个历史 Commit）。
3. 官方修复该 Bug 的标准 **Unit Test（单元测试）**。



传统的 AI 评测（如问答、写个小函数）只需看输出文本像不像，而 SWE-bench 则是**真刀真枪地让 AI 去改大型复杂项目的代码**，并通过跑通测试用例来决定成败。

---

### 二、 评估阶段的运作机制（为什么是“零 Token 消耗”？）

正如你所说，在 `run_evaluation` 这一步：

1. **大模型已经退场**：大模型的工作在上一步（生成 `predictions.jsonl`）就已经全部完成了。
2. **纯确定性流程**：这一步不需要再调用任何大模型 API（所以**零 Token 消耗**、不花钱）。它只是一个本地的**机械化自动化脚本**：
* 启动 Docker 容器配置好代码运行环境。
* 把大模型生成的修复方案（Patch）应用到代码里。
* 运行该项目自带的测试命令（如 `pytest` 或 `unittest`）。
* 如果测试全部通过，说明 AI 成功修好了 Bug；如果有报错，说明没修好。



---

### 三、 什么是 `git diff`？

`git diff` 是版本控制工具 **Git** 的一个核心命令，意思是“查看差异（Differences）”。

在 SWE-bench 和大模型代码生成中，`git diff` 通常指代“代码补丁（Patch）”**。它精确记录了**改动了哪几个文件、在哪一行删除了什么代码、增添了什么代码。

#### 1. `git diff` 长什么样？

一个典型的 `git diff` 文本片段如下：

```diff
diff --git a/calculator.py b/calculator.py
index 83db4f6..123e456 100644
--- a/calculator.py
-++ b/calculator.py
@@ -10,3 +10,3 @@ def divide(a, b):
     if b == 0:
-        raise ValueError("Cannot divide by zero")
+        raise ZeroDivisionError("除数不能为零")
     return a / b

```

#### 2. 它的各部分含义：

* **`--- a/calculator.py` 和 `+++ b/calculator.py**`：表示修改前后的文件是 `calculator.py`。
* **`-`（红色/减号开头的行）**：代表被**删除**或修改前的旧代码。
* **`+`（绿色/加号开头的行s）**：代表新**增加**或修改后的代码。
* **`@@ ... @@`**：定位坐标，说明这段改动发生在文件的第 10 行附近。

#### 3. 在 SWE-bench 中它是怎么用的？

大模型在完成思考后，不会直接把整个几万行的项目代码重新发给你，而是只输出一段符合 `git diff` 格式的文本（或者包含这段 diff 的 `predictions.jsonl` 文件）。评估脚本拿到这段 `git diff` 后，直接执行 `git apply` 命令，像贴膏药一样精准地把这几行改动“贴”进本地仓库，然后就可以开始跑 `pytest` 了。