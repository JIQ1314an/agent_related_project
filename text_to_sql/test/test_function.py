from sql_generator import get_db_schema_for_tables
import os

# Test the actual function
print("Current working directory:", os.getcwd())

result = get_db_schema_for_tables(["customers"], "../chinook.db")
print(f"Function result:\n{result}")
