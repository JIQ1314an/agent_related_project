import sys
from loguru import logger

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level:<8}</level> | <cyan>{extra[step]}</cyan> - <level>{message}</level>",
    level="INFO",
)


def get_task_logger(task_id: str, step: str = "INIT"):
    return logger.bind(task_id=task_id, step=step)
