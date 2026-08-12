from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseSkill(ABC):
    """符合 AgentSkills 标准的抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """技能的功能描述"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema 参数定义"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """技能的核心执行逻辑"""
        pass

    def to_schema(self) -> Dict[str, Any]:
        """转换为标准 Tool/Function Calling 结构"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }