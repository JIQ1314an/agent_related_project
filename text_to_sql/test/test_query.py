import os
import sqlite3
from pathlib import Path

# Test the actual function
print("Current working directory:", os.getcwd())

# Test the same query as in get_db_schema_for_tables
# db_path = (
#     "D:\\DevWorkSpace\\python_project\\ai_demo\\demo_exercise\\text_to_sql\\chinook.db"
# )

current_dir = Path(__file__).resolve().parent
db_path = current_dir / ".." / "chinook.db"
table = "customers"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"Testing query for table: '{table}'")
query = f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';"

cursor.execute(query)
result = cursor.fetchone()

print(f"Result: {result}")
if result:
    print(f"Schema: {result[0]}")
else:
    print("No result found!")

conn.close()
