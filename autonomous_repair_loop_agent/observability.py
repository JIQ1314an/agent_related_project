import os
import re
import inspect
from typing import Optional, Any, Dict, Callable
from config import settings
from logger import logger

try:
    from langfuse import Langfuse

    HAS_LANGFUSE = True
except ImportError:
    Langfuse = None
    HAS_LANGFUSE = False


def safe_call(func: Callable, *args, **kwargs) -> Any:
    """
    安全调用函数/方法：自动检测并剥离目标函数不支持的关键字参数，彻底防止 TypeError 报错。
    """
    if not callable(func):
        return None

    cur_kwargs = dict(kwargs)
    # 1. 优先通过 inspect 检查参数列表并过滤
    try:
        sig = inspect.signature(func)
        has_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if not has_var_kw:
            cur_kwargs = {k: v for k, v in cur_kwargs.items() if k in sig.parameters}
    except Exception:
        pass

    # 2. 动态捕获并剥离未预期的参数（应对动态装饰器或 C 扩展）
    while True:
        try:
            return func(*args, **cur_kwargs)
        except TypeError as te:
            err_msg = str(te)
            if "unexpected keyword argument" in err_msg:
                match = re.search(r"unexpected keyword argument '([^']+)'", err_msg)
                if match and match.group(1) in cur_kwargs:
                    bad_key = match.group(1)
                    cur_kwargs.pop(bad_key)
                    continue
            raise te


class SpanWrapper:
    """沙箱测试步骤 (Span) 封装"""

    def __init__(self, raw_span: Any = None):
        self._raw = raw_span

    def end(self, output: Any = None):
        if not self._raw:
            return
        try:
            if output is not None and hasattr(self._raw, "update"):
                safe_call(self._raw.update, output=output)

            if hasattr(self._raw, "end"):
                safe_call(self._raw.end)
        except Exception as e:
            logger.warning(f"[OBSERVABILITY] 结束 Span 异常: {str(e)}")


class GenerationWrapper:
    """大模型调用 (Generation) 封装"""

    def __init__(self, raw_gen: Any = None):
        self._raw = raw_gen

    def end(self, output: Any = None, usage: Any = None):
        if not self._raw:
            return
        try:
            if hasattr(self._raw, "update"):
                update_kwargs = {}
                if output is not None:
                    update_kwargs["output"] = output
                if usage is not None:
                    # 兼容 Langfuse 各版本的 usage 参数命名
                    update_kwargs["usage_details"] = usage
                    update_kwargs["usage"] = usage

                safe_call(self._raw.update, **update_kwargs)

            if hasattr(self._raw, "end"):
                safe_call(self._raw.end)
        except Exception as e:
            logger.warning(f"[OBSERVABILITY] 结束 Generation 异常: {str(e)}")


class TraceWrapper:
    """根节点 (Trace) 封装"""

    def __init__(self, raw_trace: Any = None):
        self._raw = raw_trace

    def span(self, name: str, input: Any = None, output: Any = None) -> SpanWrapper:
        if not self._raw:
            return SpanWrapper(None)

        try:
            raw_span = None
            kwargs = {"name": name}
            if input is not None:
                kwargs["input"] = input

            # v4 SDK 规范：在父节点 (self._raw) 实例上调用 start_observation
            if hasattr(self._raw, "start_observation"):
                kwargs["as_type"] = "span"
                raw_span = safe_call(self._raw.start_observation, **kwargs)
            elif hasattr(self._raw, "start_span"):
                raw_span = safe_call(self._raw.start_span, **kwargs)
            elif hasattr(self._raw, "span"):
                raw_span = safe_call(self._raw.span, **kwargs)

            span_obj = SpanWrapper(raw_span)
            if output is not None:
                span_obj.end(output=output)
            return span_obj
        except Exception as e:
            logger.error(f"[OBSERVABILITY ERROR] 创建 Span 失败: {str(e)}")
            return SpanWrapper(None)

    def generation(self, name: str, model: str, input: Any = None) -> GenerationWrapper:
        if not self._raw:
            return GenerationWrapper(None)

        try:
            raw_gen = None
            kwargs = {"name": name, "model": model}
            if input is not None:
                kwargs["input"] = input

            # v4 SDK 规范：在父节点 (self._raw) 实例上调用 start_observation，类型设为 generation
            if hasattr(self._raw, "start_observation"):
                kwargs["as_type"] = "generation"
                raw_gen = safe_call(self._raw.start_observation, **kwargs)
            elif hasattr(self._raw, "start_generation"):
                raw_gen = safe_call(self._raw.start_generation, **kwargs)
            elif hasattr(self._raw, "generation"):
                raw_gen = safe_call(self._raw.generation, **kwargs)

            return GenerationWrapper(raw_gen)
        except Exception as e:
            logger.error(f"[OBSERVABILITY ERROR] 创建 Generation 失败: {str(e)}")
            return GenerationWrapper(None)

    def update(self, output: Dict[str, Any]):
        if not self._raw:
            return
        try:
            if hasattr(self._raw, "update"):
                safe_call(self._raw.update, output=output)
            if hasattr(self._raw, "end"):
                safe_call(self._raw.end)
        except Exception as e:
            logger.warning(f"[OBSERVABILITY] 更新 Trace 异常: {str(e)}")


class ObservabilityManager:
    def __init__(self):
        self.client: Optional[Any] = None

        host = (
            getattr(settings, "LANGFUSE_HOST", None)
            or os.getenv("LANGFUSE_HOST")
            or os.getenv("LANGFUSE_BASE_URL")
            or "http://localhost:3000"
        )
        pk = getattr(settings, "LANGFUSE_PUBLIC_KEY", None) or os.getenv(
            "LANGFUSE_PUBLIC_KEY"
        )
        sk = getattr(settings, "LANGFUSE_SECRET_KEY", None) or os.getenv(
            "LANGFUSE_SECRET_KEY"
        )

        if HAS_LANGFUSE and pk and sk:
            try:
                self.client = Langfuse(public_key=pk, secret_key=sk, host=host)
                logger.info(f"[OBSERVABILITY] Langfuse 客户端初始化成功 (Host: {host})")
            except Exception as e:
                logger.error(f"[OBSERVABILITY ERROR] Langfuse 初始化失败: {str(e)}")
        else:
            logger.warning("[OBSERVABILITY] 未检测到有效的 Key，处于静默模式")

    def create_trace(
        self,
        name: str,
        input: Any = None,
        user_id: str = "default_user",
        metadata: dict = None,
    ) -> TraceWrapper:
        if not self.client:
            return TraceWrapper(None)

        try:
            meta = dict(metadata or {})
            if user_id and "user_id" not in meta:
                meta["user_id"] = user_id

            raw_trace = None

            # 1. 优先使用 v4 SDK start_observation
            if hasattr(self.client, "start_observation"):
                kwargs = {"name": name, "as_type": "span", "metadata": meta}
                if input is not None:
                    kwargs["input"] = input

                raw_trace = safe_call(self.client.start_observation, **kwargs)

            # 2. 次选 v4 OTEL 模式 start_as_current_observation
            elif hasattr(self.client, "start_as_current_observation"):
                kwargs = {"name": name, "as_type": "span", "metadata": meta}
                if input is not None:
                    kwargs["input"] = input

                raw_trace = safe_call(
                    self.client.start_as_current_observation, **kwargs
                )

            # 3. 兼容 v2/v3 旧版 SDK trace
            elif hasattr(self.client, "trace"):
                kwargs = {"name": name, "user_id": user_id, "metadata": meta}
                if input is not None:
                    kwargs["input"] = input

                raw_trace = safe_call(self.client.trace, **kwargs)

            if raw_trace:
                if user_id and hasattr(raw_trace, "update"):
                    safe_call(raw_trace.update, user_id=user_id)
                return TraceWrapper(raw_trace)
            else:
                logger.error(
                    "[OBSERVABILITY ERROR] 当前 Langfuse SDK 实例无可用构建方法"
                )
                return TraceWrapper(None)

        except Exception as e:
            logger.error(f"[OBSERVABILITY ERROR] 创建 Trace 失败: {str(e)}")

        return TraceWrapper(None)

    def flush(self):
        if self.client:
            try:
                safe_call(self.client.flush)
                logger.info("[OBSERVABILITY] Trace 数据已成功同步至 Langfuse 服务端！")
            except Exception as e:
                logger.error(f"[OBSERVABILITY ERROR] Flush 刷新失败: {str(e)}")


obs_manager = ObservabilityManager()
