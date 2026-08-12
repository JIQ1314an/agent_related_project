import sqlite3
from config.settings import DB_PATH


def get_db_connection():
    """生产级数据库连接获取函数，支持上下文安全管理"""
    return sqlite3.connect(DB_PATH)
