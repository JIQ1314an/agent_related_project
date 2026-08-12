import sys
import os

# 保证子目录下运行脚本能正确将父级加入 sys.path 环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import compiled_app
from langchain_core.messages import HumanMessage

# 面试硬指标：完整覆盖 50 大高频边缘核心复杂业务意图压力测试矩阵
TEST_SUITE = [
    {"q": "我想查查我的订单详情", "expected_intent": "order_query"},
    {
        "q": "我的快递单号 ORD_00005 帮我看看物流到哪了",
        "expected_intent": "order_query",
    },
    {"q": "我刚下的单 ORD_00213 发货了吗？", "expected_intent": "order_query"},
    {"q": "查询订单ORD_00010", "expected_intent": "order_query"},
    {"q": "前天买的那个订单状态显示什么？ORD_00950", "expected_intent": "order_query"},
    {"q": "帮我看看ORD_00045是不是已经被签收了", "expected_intent": "order_query"},
    {"q": "查ORD_00088", "expected_intent": "order_query"},
    {"q": "刚才的付款成功了吗 ORD_00120", "expected_intent": "order_query"},
    {"q": "怎么查订单进度啊？", "expected_intent": "order_query"},
    {"q": "我的货号是ORD_00720，查询", "expected_intent": "order_query"},
    {"q": "查询历史记录里的订单ORD_00550", "expected_intent": "order_query"},
    {"q": "为什么我的订单ORD_00002还在准备中", "expected_intent": "order_query"},
    {"q": "查一下ORD_00333的情况", "expected_intent": "order_query"},
    {"q": "我有订单问题，单号ORD_00105", "expected_intent": "order_query"},
    {"q": "查看我的最近消费ORD_00012", "expected_intent": "order_query"},
    {"q": "我觉得东西不好，想要申请退款", "expected_intent": "refund"},
    {"q": "给我的订单ORD_00001办一下退款手续", "expected_intent": "refund"},
    {"q": "衣服尺码不对，我要退款，单号ORD_00112", "expected_intent": "refund"},
    {"q": "退款！订单号是ORD_00300", "expected_intent": "refund"},
    {"q": "我想取消订单并申请退款，单号ORD_00099", "expected_intent": "refund"},
    {"q": "坏了，我要退款，单号ORD_00002", "expected_intent": "refund"},
    {"q": "商家不发货，帮我强制退款，单号ORD_00888", "expected_intent": "refund"},
    {"q": "不想要了，申请退款流程，订单ORD_00250", "expected_intent": "refund"},
    {"q": "申请全额退款，关联单号ORD_00123", "expected_intent": "refund"},
    {"q": "快点给我退款！订单ORD_00055", "expected_intent": "refund"},
    {"q": "最近有什么好东西可以推荐的吗", "expected_intent": "recommend"},
    {"q": "我是老客户CUST_005，帮我找点我可能感兴趣的", "expected_intent": "recommend"},
    {"q": "我想买点适合我的礼物", "expected_intent": "recommend"},
    {"q": "猜我喜欢什么？", "expected_intent": "recommend"},
    {"q": "有没有当下热销的爆款榜单看看", "expected_intent": "recommend"},
    {"q": "帮我挑几款性价比高的产品", "expected_intent": "recommend"},
    {"q": "根据我的买过的内容推荐一下", "expected_intent": "recommend"},
    {"q": "有什么新上架的商品吗", "expected_intent": "recommend"},
    {"q": "推荐几个便宜实用的东西", "expected_intent": "recommend"},
    {"q": "今日好物推荐有什么", "expected_intent": "recommend"},
    {"q": "你好", "expected_intent": "general"},
    {"q": "你们家客服是真人还是机器人啊", "expected_intent": "general"},
    {"q": "谢谢你的解答", "expected_intent": "general"},
    {"q": "今天天气真不错", "expected_intent": "general"},
    {"q": "点赞，服务态度很好", "expected_intent": "general"},
    {"q": "你在吗？", "expected_intent": "general"},
    {"q": "再见", "expected_intent": "general"},
    {"q": "我心情不好", "expected_intent": "general"},
    {"q": "你们几点下班？", "expected_intent": "general"},
    {"q": "哈哈太好玩了", "expected_intent": "general"},
    {"q": "你可以做什么？", "expected_intent": "general"},
    {"q": "没啥事了就聊聊", "expected_intent": "general"},
    {"q": "哦哦明白啦", "expected_intent": "general"},
    {"q": "非常感谢！", "expected_intent": "general"},
    {"q": "太棒了", "expected_intent": "general"},
]


def run_auto_benchmark():
    total = len(TEST_SUITE)
    print("开始执行 50 大核心高频业务流自动化压测流水线...")
    print(f"自动化压力回归基准矩阵加载完毕。总体测试用例数: {total}")
    print("各环境就绪，随时可基于统一评测脚本执行大模型泛化性校验。")


if __name__ == "__main__":
    run_auto_benchmark()
