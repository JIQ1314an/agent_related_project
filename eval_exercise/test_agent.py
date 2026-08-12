import os
from deepeval import assert_test
from deepeval.metrics import GEval, HallucinationMetric
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from langchain_openai import ChatOpenAI


# ----------------------------------------------------------------------
# 1. 自定义 DeepEval 的 Qwen 裁判模型封装
# ----------------------------------------------------------------------
class QwenModel(DeepEvalBaseLLM):
    def __init__(self, model_name="qwen-plus"):
        self.model_name = os.getenv("MODEL_NAME")
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("QWEN_BASE_URL")
        if not dashscope_api_key:
            raise ValueError("❌ 请先设置环境变量: export DASHSCOPE_API_KEY='sk-xxx'")

        # 复用 langchain_openai 的 ChatOpenAI 适配 DashScope
        self.model = ChatOpenAI(
            model=self.model_name,
            temperature=0,
            openai_api_key=dashscope_api_key,
            openai_api_base=base_url,
        )

    def load_model(self):
        return self.model

    def generate(self, prompt: str) -> str:
        res = self.model.invoke(prompt)
        return str(res.content)

    async def a_generate(self, prompt: str) -> str:
        res = await self.model.ainvoke(prompt)
        return str(res.content)

    def get_model_name(self):
        return self.model_name


# ----------------------------------------------------------------------
# 2. 被测 Agent 函数
# ----------------------------------------------------------------------
def mock_customer_agent(user_prompt: str) -> str:
    return "您的订单 98765 已经发货，正在运送途中。"


# ----------------------------------------------------------------------
# 3. 单元测试逻辑
# ----------------------------------------------------------------------
def test_hallucination_and_politeness():
    # 实例化千问裁判模型
    qwen_evaluator = QwenModel(model_name="qwen-plus")

    # 构造测试用例
    retrieved_context = ["订单 98765 状态：在途，承运商为顺丰速运。"]
    user_input = "我的订单 98765 到哪了？"
    actual_output = mock_customer_agent(user_input)

    test_case = LLMTestCase(
        input=user_input, actual_output=actual_output, context=retrieved_context
    )

    # 核心：将 model=qwen_evaluator 显式传给每个 Metric
    hallucination_metric = HallucinationMetric(threshold=0.5, model=qwen_evaluator)

    politeness_metric = GEval(
        name="Politeness",
        criteria="判断 Agent 输出是否使用了礼貌、客气的语气",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.7,
        model=qwen_evaluator,
    )

    # 执行断言测试
    assert_test(test_case, [hallucination_metric, politeness_metric])
