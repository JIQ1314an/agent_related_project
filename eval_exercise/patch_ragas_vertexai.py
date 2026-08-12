import sys
import types

try:
    import langchain_community.chat_models.vertexai  # noqa: F401
except ImportError:
    _vertexai_stub = types.ModuleType("langchain_community.chat_models.vertexai")

    class ChatVertexAI:
        """
        仅用于满足 ragas 0.4.3 的 import。
        当前项目使用 OpenAI 兼容接口，不会真正调用 VertexAI。
        """

        pass

    _vertexai_stub.ChatVertexAI = ChatVertexAI
    sys.modules["langchain_community.chat_models.vertexai"] = _vertexai_stub
