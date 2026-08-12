# 1. 获取当前执行脚本所在的绝对路径
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. 将相对路径与当前脚本所在目录拼接为绝对路径
DB_PATH = os.path.join(current_dir, "northwind.db")


print(f"当前脚本所在目录: {current_dir}")
print(f"数据库文件路径: {DB_PATH}")
