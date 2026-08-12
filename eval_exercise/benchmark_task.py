from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import pattern  # 1. 使用 pattern 代替 match
from inspect_ai.solver import generate, system_message, use_tools  # 导入 system_message
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
        plan=[
            # 修改点 A：增加全局 Prompt，要求模型将最终答案包在 \boxed{} 中
            # 关键修改：将 { 和 } 改为 {{ 和 }} 转义，防止被 Python 格式化引擎(str.format())误解析
            # 明确提醒大模型：先用 Python 工具进行计算，再填入 \boxed{}
            system_message(
                "你是一个具备 Python 代码执行能力的 AI 助手。\n"
                "1. 对于遇到的计算任务，请务必优先编写并执行 Python 代码来获取精确结果。\n"
                "2. 获取结果后，请务必将最终的纯数字答案写在 \\boxed{{}} 中，例如：\\boxed{{1060}}。"
            ),
            use_tools(python()),
            generate(),
        ],
        # 修改点 B：将 match() 改为 pattern()，精准匹配提取 \boxed{} 里的数值
        scorer=pattern(r"\\boxed\{([^{}]+)\}"),
    )
