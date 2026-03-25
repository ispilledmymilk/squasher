# backend/agents/velocity_agent.py

from typing import Any, Dict
from .base_agent import BaseAgent
from analyzers.git_analyzer import GitAnalyzer
from utils.logger import setup_logger

logger = setup_logger(__name__)


class VelocityAgent(BaseAgent):
    """Agent 2: Analyzes team velocity and change patterns"""

    def __init__(self, repo_path: str):
        super().__init__("VelocityAgent")
        self.git_analyzer = GitAnalyzer(repo_path)

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze change velocity for a file"""
        file_path = context.get("file_path")

        history = self.git_analyzer.analyze_file_history(file_path)

        change_frequency = history.get("change_frequency", 0)
        authors_count = history.get("authors_count", 0)
        avg_days_between = history.get("avg_days_between_changes", 0)

        churn_risk = self._calculate_churn_risk(
            change_frequency, authors_count, avg_days_between
        )

        is_hotspot = change_frequency > 10

        result = {
            "agent": self.name,
            "change_frequency": change_frequency,
            "authors_count": authors_count,
            "avg_days_between_changes": avg_days_between,
            "churn_risk_score": churn_risk,
            "is_hotspot": is_hotspot,
            "warnings": self._generate_warnings(change_frequency, authors_count),
        }

        self.log_result(result)
        return result

    def _calculate_churn_risk(
        self,
        change_frequency: int,
        authors_count: int,
        avg_days_between: float,
    ) -> float:
        """Calculate churn risk score (0-100)"""
        risk_score = 0.0

        if change_frequency > 20:
            risk_score += 30
        elif change_frequency > 10:
            risk_score += 20
        elif change_frequency > 5:
            risk_score += 10

        if authors_count > 5:
            risk_score += 20
        elif authors_count > 3:
            risk_score += 10

        if 0 < avg_days_between < 7:
            risk_score += 25
        elif avg_days_between < 14:
            risk_score += 15

        return min(100, risk_score)

    def _generate_warnings(self, change_frequency: int, authors_count: int) -> list:
        """Generate warning messages"""
        warnings = []

        if change_frequency > 15:
            warnings.append(
                f"High churn: {change_frequency} changes in 90 days."
            )

        if authors_count > 4:
            warnings.append(
                f"Multiple authors ({authors_count}) may indicate coordination issues."
            )

        if change_frequency > 20 and authors_count > 5:
            warnings.append(
                "Critical: High churn + many authors = high risk."
            )

        return warnings
