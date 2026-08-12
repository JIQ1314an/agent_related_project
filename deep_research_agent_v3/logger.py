import logging
import sys


def setup_logger(name: str = "DeepResearch") -> logging.Logger:
    """初始化双通道高可靠日志记录器（控制台 + 本地日志文件）"""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    # 统一的标准日志格式（包含时间戳、级别、文件名、代码行号）
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. 本地文件 Handler（追加模式）
    file_handler = logging.FileHandler("deep_research_system.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
