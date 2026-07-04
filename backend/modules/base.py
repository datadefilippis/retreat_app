from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseModule(ABC):
    """Abstract base class for all modules"""
    
    @property
    @abstractmethod
    def key(self) -> str:
        """Unique module identifier"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable module name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Module description"""
        pass
    
    @property
    def category(self) -> str:
        """Module category"""
        return "other"
    
    @property
    def icon(self) -> str:
        """Module icon name"""
        return "activity"
    
    @property
    def is_available(self) -> bool:
        """Whether module is available"""
        return True
    
    @abstractmethod
    async def get_kpis(self, org_id: str, period: str, **kwargs) -> Dict[str, Any]:
        """Get key performance indicators"""
        pass
    
    @abstractmethod
    async def get_charts(self, org_id: str, period: str, **kwargs) -> Dict[str, Any]:
        """Get chart data"""
        pass
