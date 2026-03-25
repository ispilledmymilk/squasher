# backend/agents/complexity_agent.py

from typing import Any, Dict
from .base_agent import BaseAgent
from analyzers.code_analyzer import CodeAnalyzer
from data.metrics_store import MetricsStore
from utils.constants import COMPLEXITY_HIGH, COMPLEXITY_VERY_HIGH
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ComplexityAgent(BaseAgent):
    """Agent 1: Analyzes code complexity trends"""

    def __init__(self):
        super().__init__("ComplexityAgent")
        self.analyzer = CodeAnalyzer()
        self.metrics_store = MetricsStore()

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze complexity metrics and trends"""
        file_path = context.get("file_path")

        current_metrics = self.analyzer.analyze_file(file_path)
        if not current_metrics:
            return {"status": "unsupported_file"}

        history = self.metrics_store.get_file_history(file_path, limit=10)

        complexity_trend = self._calculate_trend(history, "cyclomatic_complexity")
        mi_trend = self._calculate_trend(history, "maintainability_index")

        current_complexity = current_metrics.get("cyclomatic_complexity", 0)
        risk_score = self._calculate_complexity_risk(
            current_complexity, complexity_trend
        )

        result = {
            "agent": self.name,
            "current_complexity": current_complexity,
            "complexity_trend": complexity_trend,
            "maintainability_index": current_metrics.get("maintainability_index", 0),
            "mi_trend": mi_trend,
            "risk_score": risk_score,
            "warnings": self._generate_warnings(current_metrics, complexity_trend),
        }

        self.log_result(result)
        return result

    def _calculate_trend(self, history, metric_name: str) -> str:
        """Calculate if metric is increasing, decreasing, or stable"""
        if len(history) < 2:
            return "insufficient_data"

        values = [
            getattr(h, metric_name)
            for h in history
            if getattr(h, metric_name, None) is not None
        ]

        if len(values) < 2:
            return "insufficient_data"

        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid
        second_half_avg = sum(values[mid:]) / (len(values) - mid)

        if first_half_avg == 0:
            return "stable"
        change_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100

        if change_pct > 10:
            return "increasing"
        elif change_pct < -10:
            return "decreasing"
        return "stable"

    def _calculate_complexity_risk(
        self, current_complexity: float, trend: str
    ) -> float:
        """Calculate risk score (0-100) based on complexity"""
        risk_score = 0.0

        if current_complexity >= COMPLEXITY_VERY_HIGH:
            risk_score += 40
        elif current_complexity >= COMPLEXITY_HIGH:
            risk_score += 25
        else:
            risk_score += (current_complexity / COMPLEXITY_HIGH) * 15

        if trend == "increasing":
            risk_score += 25
        elif trend == "decreasing":
            risk_score -= 10

        return min(100, max(0, risk_score))

    def _generate_warnings(self, metrics: Dict, trend: str) -> list:
        """Generate warning messages"""
        warnings = []

        complexity = metrics.get("cyclomatic_complexity", 0)
        mi = metrics.get("maintainability_index", 100)

        if complexity >= COMPLEXITY_VERY_HIGH:
            warnings.append(
                f"Very high complexity ({complexity}). Consider refactoring."
            )
        elif complexity >= COMPLEXITY_HIGH:
            warnings.append(f"High complexity ({complexity}). Monitor closely.")

        if mi < 20:
            warnings.append(
                f"Very low maintainability index ({mi}). Refactor recommended."
            )

        if trend == "increasing":
            warnings.append("Complexity is increasing over time.")

        return warnings
