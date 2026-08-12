import os
import sqlite3
import datetime

# from demo_exercise.personal_mcp_assistan import config
import config
from mcp.server.fastmcp import FastMCP
import httpx

# 初始化 FastMCP 服务（定义服务名称）
mcp = FastMCP("Personal Assistant & Northwind DB Server")

# 1. 获取当前执行脚本所在的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. 将相对路径与当前脚本所在目录拼接为绝对路径
DB_PATH = os.path.join(current_dir, "northwind.db")
# DB_PATH = "northwind.db"

# ==========================================
# 🧱 1. 工具集实现 (Tools)
# ==========================================


@mcp.tool()
async def get_weather(latitude: float, longitude: float) -> str:
    """
    获取指定经纬度的实时天气预报（使用 Open-Meteo 免费 API）。
    例如：北京 (39.9, 116.4)
    """
    # 强制打印日志到终端，方便你观察 Claude 到底传了什么参数进来
    print(f" LOG: get_weather 被调用，参数: lat={latitude}, lon={longitude}")

    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"

    try:
        # 🔥 优化点 1：关闭 verify=False 防止 Windows 证书报错；设置 timeout=10 防止无限卡死
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json().get("current_weather")
                if data:
                    return f"🌤️ 实时天气：气温 {data['temperature']}°C，风速 {data['windspeed']}km/h，天气代码 {data['weathercode']}"
                return "❌ API 成功响应，但未找到 current_weather 数据结构。"

            return f"❌ 天气数据获取失败，API 状态码：{response.status_code}"

    except Exception as e:
        # 🔥 优化点 2：如果网络彻底断开或报错，把真实报错吐给大模型，大模型就会在界面上告诉你为什么错，而不是敷衍你
        return f"❌ 本地 Python 代码执行网络异常，报错原因: {str(e)}"


@mcp.tool()
async def search_news(query: str) -> str:
    """
    通过关键字搜索最新的全球新闻（使用 NewsAPI 免费接口）。
    """
    api_key = config.news_api_key
    if api_key.strip() == "":
        return "⚠️ 请先在 server.py 中配置您的 NewsAPI 密钥。"

    url = f"https://newsapi.org/v2/everything?q={query}&pageSize=3&apiKey={api_key}"
    #  关闭 SSL 验证（verify=False）会让你的网络连接极易受到中间人攻击（MITM），绝对不要在生产环境或正式上线的项目中使用此方法。
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url)
        if response.status_code == 200:
            articles = response.json().get("articles", [])
            if not articles:
                return "🔍 未找到相关新闻。"
            res = []
            for a in articles:
                res.append(
                    f"📰 【{a['title']}】\n来源: {a['source']['name']}\n简介: {a['description']}\n---"
                )
            return "\n".join(res)
        return f"❌ 新闻搜索失败，错误码：{response.status_code}"


@mcp.tool()
def calculate_expression(expression: str) -> str:
    """
    一个安全的数学计算器，支持加减乘除、括号等复合运算。输入如: (12 + 35) * 2
    """
    import ast
    import operator

    # 定义安全的操作符，防止 eval 注入漏洞
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }

    def eval_node(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return operators[type(node.op)](eval_node(node.left), eval_node(node.right))
        elif isinstance(node, ast.UnaryOp):
            return operators[type(node.op)](eval_node(node.operand))
        else:
            raise TypeError(f"不支持的数学操作: {type(node)}")

    try:
        node = ast.parse(expression, mode="eval").body
        result = eval_node(node)
        return f"🔢 计算结果: {expression} = {result}"
    except Exception as e:
        return f"❌ 计算器语法错误: {str(e)}"


@mcp.tool()
def manage_schedule(action: str, content: str = "", item_id: int = None) -> str:
    """
    个人日程管理工具（本地 SQLite 驱动）。
    action 参数可选:
    - 'add': 添加日程 (需提供 content)
    - 'list': 列出所有日程
    - 'delete': 删除指定日程 (需提供 item_id)
    """
    # 日程保存在本地数据库中
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 动态创建日程表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mcp_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            content TEXT
        )
    """)
    conn.commit()

    if action == "add":
        if not content:
            return "⚠️ 错误：添加日程必须提供 content"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO mcp_schedule (time, content) VALUES (?, ?)", (now, content)
        )
        conn.commit()
        res = "✅ 日程记录成功！"
    elif action == "list":
        cursor.execute("SELECT id, time, content FROM mcp_schedule ORDER BY id DESC")
        rows = cursor.fetchall()
        if not rows:
            res = "📅 当前日程表为空。"
        else:
            res = "\n".join([f"[{r[0]}] {r[1]} : {r[2]}" for r in rows])
    elif action == "delete":
        if item_id is None:
            return "⚠️ 错误：删除日程必须提供 item_id"
        cursor.execute("DELETE FROM mcp_schedule WHERE id = ?", (item_id,))
        conn.commit()
        res = f"🗑️ 已成功删除 ID 为 {item_id} 的日程。"
    else:
        res = "⚠️ 未知的操作指令。"

    conn.close()
    return res


@mcp.tool()
def execute_query(sql: str) -> str:
    """
    执行对 Northwind 数据库的 SQL 查询。安全限制：为了防止删库，仅允许 SELECT 语句。
    """
    if not sql.strip().upper().startswith("SELECT"):
        return "❌ 安全错误：该工具仅支持 SELECT 查询，禁止执行破坏性修改。"

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        # cursor.description用于获取关于上一次查询结果集的列信息（对应 DB-API 2.0 规范），(column_name, type_code, display_size, internal_size, precision, scale, null_ok)
        # 提取列名
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if not rows:
            return "查无结果。"

        # 拼装前 10 条结果返回（防止数据量过大导致 LLM 上下文爆炸）
        output = [
            f"| {' | '.join(columns)} |",
            "| " + " | ".join(["---"] * len(columns)) + " |",
        ]
        for row in rows[:10]:
            output.append(f"| {' | '.join(str(item) for item in row)} |")

        if len(rows) > 10:
            output.append(f"\n*(数据过多，已省略其余 {len(rows)-10} 条结果)*")

        return "\n".join(output)
    except Exception as e:
        return f"❌ SQL 执行报错: {str(e)}"


# ==========================================
# 📊 2. 资源库实现 (Resources)
# ==========================================


@mcp.resource("schema://tables")
def get_schema() -> str:
    """
    获取当前 Northwind 数据库的关键表结构（Schema DDL），方便大模型查阅和生成高正确率的 SQL。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # 获取所有非系统表名
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        tables = [r[0] for r in cursor.fetchall()]

        ddl_list = []
        for t in tables[:8]:  # 挑选前 8 张核心表展示，节约上下文
            cursor.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{t}';"
            )
            ddl = cursor.fetchone()
            if ddl:
                ddl_list.append(ddl[0])

        conn.close()
        return "【Northwind 数据库核心 Schema 结构】\n\n" + "\n\n".join(ddl_list)
    except Exception as e:
        return f"无法获取 Schema: {str(e)}"


# ==========================================
# 💡 3. 提示词模板实现 (Prompts)
# ==========================================


@mcp.prompt()
def sales_report() -> str:
    """
    销售分析提示词模板。快速指导大模型如何针对 Northwind 数据库生成业务分析报告。
    """
    return """你现在是一位精通 Northwind 数据库的资深商业分析师。请按下述步骤帮我出一份销售分析报告：
1. 首先主动查看 `schema://tables` 资源获取表结构。
2. 编写一条 SQL 查询，通过 `execute_query` 获取总销售额最高的前 5 个产品（提示：需要结合 Order Details 和 Products 表）。
3. 结合返回的数据，帮我撰写一份 200 字以内的专业商业趋势简报。"""


@mcp.prompt()
def sales_report1(year: str) -> str:
    """
    一个帮助销售总监生成年度 Northwind 数据库销售报告的专业提示词模板。
    """
    return f"""
你现在是一位资深的商业数据分析师。请结合我的本地数据库，帮我分析 {year} 年度的销售情况。
请严格按照以下步骤执行：
1. 首先，使用 `execute_query` 工具查询 {year} 年各月份的总销售额（注意过滤订单日期 `OrderDate`）。
2. 其次，找出该年度贡献额最高的前 3 名大客户。
3. 最终，请结合数据为我输出一份图表渲染（Markdown表格）以及一份不少于 200 字的季度市场洞察报告。
"""


if __name__ == "__main__":
    # 启动 MCP 服务
    mcp.run()
