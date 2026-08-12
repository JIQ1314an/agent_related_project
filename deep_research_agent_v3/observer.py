import os
from typing import Optional
from config import settings
from logger import logger

# 优先导入新版 Langfuse SDK，降级兼容旧版
try:
    from langfuse.langchain import CallbackHandler
except ImportError:
    try:
        from langfuse.callback import CallbackHandler
    except ImportError:
        CallbackHandler = None


def init_langfuse_callback() -> Optional[object]:
    """初始化 LangFuse 回调句柄以捕获 API 调用链路"""
    if CallbackHandler is None:
        logger.warning("[Observer] 未检测到 langfuse 安装包，全链路追踪将自动关闭。")
        return None

    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        logger.info("[Observer] 正在初始化 LangFuse 全链路 Trace 回调...")

        # 核心：将配置统一写入环境变量，这是 Langfuse SDK 官方标准的认证方式
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
        if settings.LANGFUSE_HOST:
            os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST

        try:
            # 直接进行无参初始化，SDK 会自动识别上面的环境变量
            handler = CallbackHandler()
            logger.info("[Observer] LangFuse 全链路 Trace 回调初始化成功！")
            return handler
        except Exception as e:
            logger.error(f"[Observer] Langfuse 初始化失败: {e}")
            return None
    else:
        logger.warning(
            "[Observer] 未提供 LangFuse Key，系统将在无分布式 Trace 模式下运行。"
        )
        return None
