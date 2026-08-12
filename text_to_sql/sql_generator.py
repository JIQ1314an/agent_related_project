# sql_generator.py
import sqlite3

from openai import OpenAI
import json
from config import qwen_api_key, qwen_base_url, model_name


from pydantic import BaseModel, Field
from typing import List


# 1. 结构化输出模型不变
class SQLGenerationResult(BaseModel):
    thought: str = Field(description="生成 SQL 的思考过程，包括如何关联表和筛选条件")
    sql_query: str = Field(
        description="最终生成的、可直接在 SQLite 中执行的 SQL 语句，不要包含 md 格式标记"
    )
    used_tables: List[str] = Field(description="该 SQL 语句中实际使用到的数据库表名")


# 2. 🔥 优化后的 Schema 提取函数：按需加载
def get_db_schema_for_tables(
    target_tables: List[str], db_path: str = "chinook.db"
) -> str:
    """
    不要盲目地把整个数据库的所有字段和几千条数据都塞给大模型。最优雅、最省 token 的方式是提取核心表的建表语句（DDL）
    自动获取 Chinook 的表结构

    只获取指定表的 DDL，避免全量 Schema 污染
    """
    if not target_tables:
        return "未指定任何表结构。"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    schema_texts = []

    for table in target_tables:
        table = table.strip().lower()  # 去除表名两端的空格并转为小写
        # SQLite 查 DDL
        cursor.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';"
        )
        result = cursor.fetchone()
        if result:
            schema_texts.append(result[0])

    conn.close()
    return "\n\n".join(schema_texts)


# 3. 大模型交互逻辑
client = OpenAI(api_key=qwen_api_key, base_url=qwen_base_url)

SYSTEM_PROMPT = """你是一个精通 SQLite 的专家。你的任务是将用户的自然语言问题转换为符合标准的 SQLite 查询语句。

【核心规则】
1. 只能使用提供的数据库 Schema 中存在的表和列。
2. 注意映射关系：用户说“产品/歌曲”对应 `tracks` 表，“订单”对应 `invoices` 表，“类别/流派”对应 `genres` 表, “订单明细”对应 `invoice_items` 表。
3. 严格按照要求的 JSON 结构返回，必须包含 'sql_query', 'thought', 'used_tables' 这三个字段，切勿遗漏。
"""


def generate_sql(question: str, schema: str) -> SQLGenerationResult:
    user_content = f"""数据库结构 (DDL) 如下：
{schema}

用户问题：{question}
请生成对应的 SQL 语句。"""

    # 配合 OpenAI/DeepSeek 的 JSON Mode 或 Structured Outputs
    response = client.beta.chat.completions.parse(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=SQLGenerationResult,
        temperature=0.0,  # 严谨任务，温度设为 0
    )

    return response.choices[0].message.parsed


# 3. 测试生成的sql
def execute_sql(sql: str, db_path: str = "chinook.db"):
    """
    拿到 SQL 后，我们需要在 SQLite 中跑一下。如果报错（比如大模型虚构了字段），我们需要捕捉这个异常。
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        # 获取列名
        columns = [description[0] for description in cursor.description]
        conn.close()
        return {"success": True, "data": results, "columns": columns, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "columns": None, "error": str(e)}
