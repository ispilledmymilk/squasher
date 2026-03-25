# backend/agents/base_agent.py

from abc import ABC, abstractmethod
from typing import Any, Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, name: str):
        self.name = name
        logger.info(f"Agent initialized: {self.name}")

    @abstractmethod
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform analysis"""
        pass

    def log_result(self, result: Dict[str, Any]):
        """Log analysis result"""
        logger.debug(f"{self.name} result: {result}")
