import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logger(service_name: str = "agent-backend") -> logging.Logger:
    """
    配置工业级结构化 JSON 日志记录器，带时间戳、服务名和日志级别
    确保全链路 Trace 能够精确定位关键节点
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(filename)s %(lineno)d %(message)s",
            timestamp=True,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()
