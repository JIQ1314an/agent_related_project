# 一、 系统架构与工作流设计
整个系统由 5 个高度分工的 Agent 协作完成，并通过质量评估节点形成自主闭环机制（Feedback Loop）：

```
                            [课题输入 Topic]
                                    │
                                    ▼
                          ┌──────────────────┐
                          │ Research Planner │ (生成/优化研究计划)
                          └─────────┬────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │   Web Searcher   │ (调用 Tavily API)
                          └─────────┬────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │ Document Analyzer│ (提炼关键论点与引用)
                          └─────────┬────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  Report Writer   │ (撰写 2000+ 字报告)
                          └─────────┬────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                  ┌───────│ Quality Reviewer │ (审核质量 & 评估字数)
                  │       └─────────┬────────┘
                  │                 │
            [未通过 / 补充]        [审核通过]
                  │                 │
                  └─────────────────┼────────┐
                                    ▼        ▼
                              (重新迭代) [最终报告输出 .md]
```

系统拓展架构与断点续传原理

```
                         [Web UI / Streamlit 控制台]
                                      │
                        ┌─────────────┴─────────────┐
                        │  新建任务 (New)            │  恢复任务 (Resume)
                        ▼                           ▼
            graph.invoke(initial_state)    graph.invoke(None)  <-- 自动加载最新快照
                        │                           │
                        └─────────────┬─────────────┘
                                      ▼
                             ┌──────────────────┐
                             │ LangGraph Engine │
                             └────────┬─────────┘
                                      │
                       (每完成一个 Agent 节点，自动写入快照)
                                      │
                                      ▼
                           [(SQLite) checkpoints.db]
```
核心实现逻辑
- 线程隔离 (thread_id)：每个任务分配唯一的 thread_id（如 task-a1b2c3d4）。
- 中断判定：假定在节点 3（Document Analyzer）完成后系统崩溃，SQLite 中已保存了前 3 个节点的输出。
- 恢复运行：再次调用 workflow.resume(thread_id) 时，将输入设为 None。LangGraph 会在 SQLite 中检索 thread_id 的最新记录，跳过节点 1~3，直接进入节点 4（Report Writer）继续执行！


# 二、 详细落地流程步骤

## ① 环境准备与依赖安装

*前置条件*  
配置 Python 3.10+ 环境，安装 `langgraph`、`langchain-openai`、`tavily-python`、`pydantic` 及 `langfuse` 可观测性套件。

## ② 模型与配置管理 (config.py & logger.py)

*基础设施*  
构建全局集中式配置与日志系统。引入结构化日志输出，确保在终端与本地文件同时记录节点流转、API 响应及状态变更。

## ③ 状态数据结构设计 (models.py)

*数据流转*  
使用 `Pydantic` 定义全局状态 `State` 及各个 Agent 的输入/输出 Schema（如 `ResearchPlan`、`QualityReview`），保证数据强类型约束。

## ④ 核心 Agent 节点开发 (agents/)

*智能体实现*  
实现 Planner、Searcher、Analyzer、Writer 和 Reviewer 5 个独立 Agent。为 LLM 绑定 Structured Output，确保输出格式严格符合预期。

## ⑤ 状态图编排与反馈回路 (workflow.py)

*Graph 引擎*  
基于 `LangGraph` 建立有向有环图（DAG + Loop）。定义条件边（Conditional Edge）：若 Reviewer 评分小于 80 分且未达到最大循环上限，则携带修改意见自动返回 Planner 重新检索与补全。

## ⑥ 可观测性集成与主程序入口 (observer.py & main.py)

*生产交付*  
接入 `LangFuse` 全流程链路追踪，并在 CLI 入口中预置 10 大核心研究课题，自动执行全套流程并导出报告。


## 其他新增
1. 引入 streamlit 打造 Web 界面，引入 langgraph-checkpoint-sqlite 实现本地持久化数据库存储。
2. 在 LangGraph 编译时挂载 SqliteSaver，并暴露 resume() 及 get_task_status() 方法供前端调用。
3. 实现 Streamlit 前端交互界面，支持课题选择、实时状态提示、断点快照检索、报告渲染与一键导出。


# 三、 完整项目代码实现
项目结构目录如下：
```
deep_research_agent/
│── .env.example            # 环境变量模板
│── requirements.txt        # 项目依赖清单
│── config.py               # 全局配置管理
│── logger.py               # 工业级日志模块
│── models.py               # Pydantic 类型定义与状态模型
│── observer.py             # LangFuse 追踪封装
│── tools/
│   ├── __init__.py
│   └── registry.py         # 中央工具注册表
│   └── search_tool.py      # Tavily API 检索封装
│   └── arxiv_tool.py       # arXin 前沿论文 检索封装
│   └── github_tool.py      # 开源项目/代码仓库/SDK/架构设计检索
│   └── bocha_tool.py       # 内深度社区/微信公众号/知乎/国内技术博客与企业落地实践检索 (博查 AI)
│── agents/
│   ├── __init__.py
│   ├── planner.py          # 研究计划制定 Agent
│   ├── searcher.py         # 网络检索执行 Agent
│   ├── analyzer.py         # 文档分析与引用提取 Agent
│   ├── writer.py           # 深度报告撰写 Agent
│   └── reviewer.py         # 报告质量审核 Agent
│── workflow.py             # LangGraph 多 Agent 编排引擎
└── main.py                 # CLI 系统启动入口
└── app.py                  # Web 页面启动入口
```



# 四、测试
## 1.启动 Web 页面
在终端中执行以下命令，启动 Streamlit 控制台： 

`streamlit run app.py`

浏览器会自动打开 http://localhost:8501。
在终端中执行以下命令，启动 Streamlit 控制台： 

`streamlit run app.py`

浏览器会自动打开 http://localhost:8501。

## 2.测试“断点续传”功能
为了真实验证高可用性与故障恢复逻辑：

模拟故障：在 Web 上提交一个任务（记录生成的 Thread ID，如 task-12345）。当日志显示 Web Searcher 执行完毕、正处于 Report Writer 阶段时，在终端使用 Ctrl + C 强制终止 Python 进程（模拟网络中断或 API 报错崩盘）。

重新启动：再次运行 streamlit run app.py。

断点恢复：切换侧边栏到 【🔄 断点续传 / 恢复任务】 模式，填入 task-12345 并点击 ▶️ 恢复并继续运行。

验证效果：观察终端日志，系统将直接从 Report Writer 节点恢复，前期的 Tavily 网络检索与文档提炼完全不需要重新调用，省时且避免浪费 API 配额！

# 五、部分重构
## 重构1 加入Tool注册机制
### 最佳工程实践：Tool 自注册与动态自检机制 (Tool Registry)
标准的解法是引入 Tool 注册表 (Tool Registry) + 动态反射 (Introspection)：

1. Tool 成为“一等公民”：每个 Tool 内部自带 name 和 description（甚至可以直接继承 LangChain 的 BaseTool 或 @tool 装饰器）。

2. Planner 动态感知 Tool 库：PlannerAgent 运行时，自动向 Tool 注册表“询问”当前有哪些可用工具及其描述，动态拼接系统提示词。

3. Enum 强类型断崖校验：models.py 中使用 Enum 枚举类型，确保大模型生成的 JSON 绝对不可能超出预设工具范围。

### 这套重构带来的工业级好处
1. 零幻觉保证：因为 models.py 中使用 List[ToolType]，OpenAI 生成 JSON 时，Schema 会直接声明 enum: ["web", "bocha", "arxiv", "github"]，大模型物理上无法输出这 4 个以外的词。

2. 极佳的可扩展性：假设下周你想接入一个新的工具（如 GoogleScholarSearchTool）：

      - 你只需要在 registry.py 里定义 GOOGLE_SCHOLAR = "google_scholar"，并在字典里配置 name、description 和 instance。

      - planner.py 和 searcher.py 一行代码都不用改！ Planner 会自动读取新工具的描述，Searcher 会自动调度，这才是真正的面向对象与高内聚解耦设计！

## 重构2 引入意图路由

深入剖析：为什么通用 Prompt 生成的内容会“水”？
1. 核心瓶颈在 Writer，而不是 Reviewer
之前我们优化了 Planner 和 Reviewer，但负责实际产出文章的 WriterAgent Prompt 依然很笼统：

“撰写一篇结构严谨、内容详实的高质量研究报告...”

对于“人活一世是为什么”这种大课题，缺乏深度约束的 Writer 会自动套用大模型的经典模板：

第一段：引言（人生是一个永恒的课题...）

第二段：哲学视角（存在主义、儒家思想...）

第三段：现实意义（寻找自我、建立连接...）

第四段：总结（保持积极心态，勇敢面对...）

这种文章逻辑完全通顺，Reviewer 确实挑不出毛病（打了 88 分通过），但读起来就是“没有灵魂的废话组合”。

2. 搜索源带来的“知识平庸化”
搜索工具（Bocha/Web）抓取“人生意义”时，返回的大多是知乎回答、博客摘要或鸡汤文章。Writer 如果只是把这些资料“整理汇总”，内容质量自然上限不高。

终极解决方案：引入“领域意图路由 (Domain Routing)”
真正顶级的 Deep Research 系统，绝不应该用一套通用 Prompt 打天下。

正确的架构是：在 Planner 拆解任务时，自动识别课题类型（如：科技技术/哲学人文/商业产业），然后动态调用该领域专属的“深度 Prompt”。

```
                ┌──> [Tech Prompt] ───> 强调：架构图、对比表、代码/Benchmark、工程瓶颈
用户课题 ──> Planner分类 ──┼──> [Philosophy Prompt] ───> 强调：概念演变、流派博弈、思想实验、现实困境解法
                └──> [Business Prompt] ───> 强调：产业链、财务数据、竞争格局、政策风险
```

## 六、Agent具体工作

### 6.1  5 大 Agent 核心功能与职责分析

#### 1. PlannerAgent（课题规划与分类专家）

* **核心职责**：系统的“大脑与战略家”，负责**课题识别**与**任务拆解**。
* **核心要点**：
* **分类识别 (`category`)**：判断课题属于 `tech`（科技）、`philosophy`（人文哲学）、`business`（商业）还是 `general`（通用），为 downstream 节点提供路由依据。
* **MECE 拆解**：将复杂课题拆解为 3 到 5 个互不重叠、相互支撑的子研究任务。
* **通道路由 (`source_types`)**：根据子任务性质动态指定检索通道（`web`, `bocha`, `arxiv`, `github`）。
* **Query 转换**：针对不同工具转换格式（如遇到 `arxiv` 通道，强制将中文 Query 翻译为专业英文学术关键词）。



#### 2. SearcherAgent（多源工具调度与检索专家）

* **核心职责**：系统的“情报收集员”，负责**工具调度**与**多通道数据抓取**。
* **核心要点**：
* **注册表驱动**：通过 `ToolRegistry` 中央注册表解耦调度具体工具实例。
* **强健性与降级**：针对 arXiv 等海外源使用原生 `requests` + XML 解析并加上超时控制，防止 SSL/EOF 连接异常打断流程。
* **多源并行**：同时向全球网页（Tavily）、国内深度生态/公众号（博查）、学术论文（arXiv）、开源代码库（GitHub）发起精准检索。



#### 3. AnalyzerAgent（情报清洗与信息蒸馏专家）

* **核心职责**：系统的“数据分析师”，负责**去噪提炼**与**知识关联**。
* **核心要点**：
* **长文本去噪**：剔除检索到的无关网页广告、重复内容与无效 HTML。
* **信息蒸馏**：提取关键事实、核心数据、代码片段与架构观点，保留原始标题与 URL 追溯地址。
* **结构化组装**：将分散的多通道数据整理为高浓缩的 `analyzed_docs`，避免超长垃圾信息干扰 LLM 写作。



#### 4. WriterAgent（领域自适应撰稿专家）

* **核心职责**：系统的“首席撰稿人”，负责**长文生成**与**修订迭代**。
* **核心要点**：
* **Prompt 动态注入**：根据 Planner 提供的 `category` 自动切换专属 System Prompt（如 `tech` 启用首席 AI 架构师 Prompt；`philosophy` 启用哲学家/思想家 Prompt）。
* **闭环修订**：在后续迭代循环中，读取 Reviewer 提供的 `feedback` 意见进行针对性补全与修补。
* **硬性指标把控**：硬性约束字符数 $\ge 2000$ 字，强制 Markdown 章节结构、对比表格，并逐句嵌入 `[来源标题](URL)` 溯源链接。



#### 5. ReviewerAgent（出版级质量审查专家）

* **核心职责**：系统的“总编辑”，负责**质量把关**与**反馈生成**。
* **核心要点**：
* **多维结构化审查**：返回 `QualityReview` 对象（包含 `passed` 布尔值、`score` 打分、`word_count` 字数、`missing_aspects` 缺失项、`feedback` 修改意见）。
* **幻觉与截断控制**：`temperature` 设为 `0.0` 杜绝复读死循环，约束 `feedback` 在 300 字以内，防止 JSON 输出截断崩溃。
* **优雅降级**：若发生网络超时或解析异常，触发 `Auto-Pass` 机制保障工作流安全平滑完成。



### 6.2 结合用户课题的端到端流程分析举例

以用户输入课题：**`"大模型 Agent 架构中的 MCP (Model Context Protocol) 协议原理与工程落地挑战"`** 为例，看整个系统如何协同运转：

```
[用户输入] ➔ [Planner] ➔ [Searcher] ➔ [Analyzer] ➔ [Writer] ➔ [Reviewer] ➔ [导出报告]
                                                         ▲          │
                                                         └─ (未通过) ┘

```

#### 1. 节点 1: PlannerAgent 启动

* **分类识别**：判断该课题为硬核 AI 技术，判定 `category = "tech"`。
* **任务拆解**：
* *子任务 1*：MCP 协议的核心设计理念与架构规范（指定通道：`web`, `github`）。
* *子任务 2*：MCP 在 Agent 上下文交互中的传输协议与消息格式（指定通道：`arxiv`，自动转换 Query 为 `"Model Context Protocol agent architecture"`）。
* *子任务 3*：国内 AI 社区/微信公众号对 MCP 的实践探讨与选型对比（指定通道：`bocha`，Query 为 `"MCP协议 Agent落地 实践案例"`）。



#### 2. 节点 2: SearcherAgent 执行

* 分别向 Tavily、GitHub API、arXiv API（XML解析）和博查 AI 发起并发检索。
* 返回原始数据：涵盖 Anthropic 官方 MCP 规范文档、GitHub 开源 SDK 仓库、arXiv 相关论文摘要、知乎/微信公众号深度解析文章。

#### 3. 节点 3: AnalyzerAgent 蒸馏

* 清洗格式，剔除重复文本，提炼出：
* MCP 的三种核心角色（Client, Host, Server）。
* JSON-RPC 2.0 传输层细节。
* 包含来源链接的 Markdown 引用对，生成高纯度的 `analyzed_docs`。



#### 4. 节点 4: WriterAgent 撰写 (第 1 次运行)

* 读取到 `category = "tech"`，**动态激活 `WRITER_TECH_SYSTEM_PROMPT**`（首席 AI 架构师人设）。
* 生成初稿，包含：
* `## 1. 执行摘要`
* `## 2. 核心技术原理`（详细展开 JSON-RPC 消息架构）
* `## 3. 落地实践与工程选型`
* `## 4. 技术对比与性能瓶颈`（内嵌与 OpenAPI/Function Calling 的对比 Markdown 表格）
* `## 5. 未来演进`
* `## 6. 参考文献`（全部带有 `[标题](URL)` 追溯链接）


* 报告总字符数达到 2450 字。

#### 5. 节点 5: ReviewerAgent 审查

* 审查评定：
* `passed`: `True`
* `score`: `92.0`
* `missing_aspects`: `["未探讨 MCP 在边缘端(Edge)的序列化性能开销", "缺少多语言 SDK 完整度对比"]`
* `feedback`: `"报告结构严密，技术原理阐述清晰，对比表格专业，已满足高标准出版要求。"`



#### 6. 工作流终止与输出

* Workflow 检测到 `passed == True`，跳出循环，输出包含全量 Markdown 追溯链接的深度研究报告并存盘。