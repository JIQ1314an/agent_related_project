import logging
import sys
from colorama import Fore, Style, init

init(autoreset=True)

class AgentLogger:
    """工业级结构化格式控制日志器"""
    
    @staticmethod
    def setup_logger(name: str = "HermesAgent") -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                f"{Fore.CYAN}[%(asctime)s]{Style.RESET_ALL} [%(levelname)s] [%(name)s] -> %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            
        return logger

logger = AgentLogger.setup_logger()

def log_step(node_name: str, detail: str):
    """关键节点日志输出"""
    logger.info(f"{Fore.YELLOW}=== [NODE: {node_name}] ==={Style.RESET_ALL}\n{detail}")

def log_error(node_name: str, error_msg: str):
    """节点报错日志输出"""
    logger.error(f"{Fore.RED}!!! [ERROR AT: {node_name}] !!!{Style.RESET_ALL}\n{error_msg}")