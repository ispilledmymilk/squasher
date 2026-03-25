# backend/ml/decay_predictor.py

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from utils.config import config
from utils.constants import (
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class DecayPredictor:
    """Predict future decay score using time-series features"""

    def __init__(self):
        self.model = None
        self.model_path = os.path.join(config.MODEL_PATH, "decay_model.pkl")
        if SKLEARN_AVAILABLE:
            self._load_or_create_model()

    def _load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Loaded decay model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Error loading model: {e}. Creating new model.")
                self._create_model()
        else:
            self._create_model()

    def _create_model(self):
        """Create new Random Forest model"""
        if not SKLEARN_AVAILABLE:
            return
        self.model = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=42
        )
        logger.info("Created new decay prediction model")

    def predict_decay(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """Predict decay score and risk level"""

        decay_score = self._calculate_decay_score(agent_results)
        risk_level = self._determine_risk_level(decay_score)
        predicted_issues = self._predict_issues(agent_results, decay_score)
        optimal_date = self._calculate_optimal_refactor_date(
            decay_score, agent_results
        )
        recommendations = self._generate_recommendations(
            agent_results, decay_score
        )

        return {
            "decay_score": round(decay_score, 2),
            "risk_level": risk_level,
            "confidence": 0.75,
            "predicted_issues": predicted_issues,
            "optimal_refactor_date": optimal_date,
            "recommendations": recommendations,
        }

    def _extract_features(self, agent_results: Dict[str, Any]):
        """Extract features for ML model (for future use)"""
        if not SKLEARN_AVAILABLE:
            return None
        features = []
        complexity_data = agent_results.get("complexity", {})
        features.append(complexity_data.get("current_complexity", 0))
        features.append(
            1 if complexity_data.get("complexity_trend") == "increasing" else 0
        )
        velocity_data = agent_results.get("velocity", {})
        features.append(velocity_data.get("change_frequency", 0))
        features.append(velocity_data.get("authors_count", 0))
        dependency_data = agent_results.get("dependency", {})
        features.append(dependency_data.get("import_count", 0))
        features.append(dependency_data.get("dependency_depth", 0))
        pattern_data = agent_results.get("pattern", {})
        features.append(pattern_data.get("pattern_matches", 0))
        features.append(pattern_data.get("bug_pattern_matches", 0))
        return np.array(features).reshape(1, -1)

    def _calculate_decay_score(self, agent_results: Dict[str, Any]) -> float:
        """Calculate decay score from agent results (rule-based for MVP)"""
        weights = {
            "complexity": 0.30,
            "velocity": 0.25,
            "dependency": 0.20,
            "pattern": 0.25,
        }

        complexity_risk = agent_results.get("complexity", {}).get(
            "risk_score", 0
        )
        velocity_risk = agent_results.get("velocity", {}).get(
            "churn_risk_score", 0
        )
        dependency_risk = agent_results.get("dependency", {}).get(
            "dependency_risk_score", 0
        )
        pattern_risk = agent_results.get("pattern", {}).get(
            "pattern_risk_score", 0
        )

        decay_score = (
            complexity_risk * weights["complexity"]
            + velocity_risk * weights["velocity"]
            + dependency_risk * weights["dependency"]
            + pattern_risk * weights["pattern"]
        )

        return min(100, max(0, decay_score))

    def _determine_risk_level(self, decay_score: float) -> str:
        """Determine risk level from decay score"""
        if decay_score >= 80:
            return RISK_CRITICAL
        elif decay_score >= 60:
            return RISK_HIGH
        elif decay_score >= 40:
            return RISK_MEDIUM
        return RISK_LOW

    def _predict_issues(
        self, agent_results: Dict[str, Any], decay_score: float
    ) -> List[Dict]:
        """Predict likely future issues"""
        issues = []

        complexity_data = agent_results.get("complexity", {})
        if complexity_data.get("complexity_trend") == "increasing":
            issues.append(
                {
                    "type": "complexity_growth",
                    "description": "Complexity is increasing - may become unmaintainable",
                    "probability": 0.7,
                    "timeframe": "3-6 months",
                }
            )

        velocity_data = agent_results.get("velocity", {})
        if velocity_data.get("is_hotspot"):
            issues.append(
                {
                    "type": "high_churn",
                    "description": "High change frequency indicates instability",
                    "probability": 0.65,
                    "timeframe": "1-3 months",
                }
            )

        pattern_data = agent_results.get("pattern", {})
        for similar_issue in pattern_data.get("similar_issues", []):
            issues.append(
                {
                    "type": similar_issue.get("type", "pattern_match"),
                    "description": f"Similar to known {similar_issue.get('type', 'bug')} pattern",
                    "probability": 0.6,
                    "timeframe": "2-4 months",
                }
            )

        return issues

    def _calculate_optimal_refactor_date(
        self, decay_score: float, agent_results: Dict[str, Any]
    ) -> str:
        """Calculate when to refactor based on velocity and decay"""
        velocity_data = agent_results.get("velocity", {})
        avg_days_between = velocity_data.get(
            "avg_days_between_changes", 30
        )

        if decay_score >= 70 and avg_days_between < 14:
            days_until = 30
        elif decay_score >= 60:
            days_until = 60
        elif decay_score >= 40:
            days_until = 90
        else:
            days_until = 180

        optimal_date = datetime.now() + timedelta(days=days_until)
        return optimal_date.isoformat()

    def _generate_recommendations(
        self, agent_results: Dict[str, Any], decay_score: float
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        complexity_data = agent_results.get("complexity", {})
        for warning in complexity_data.get("warnings", []):
            recommendations.append(warning)

        velocity_data = agent_results.get("velocity", {})
        if velocity_data.get("is_hotspot"):
            recommendations.append(
                "Consider splitting this frequently-changed file into smaller modules"
            )

        dependency_data = agent_results.get("dependency", {})
        if dependency_data.get("import_count", 0) > 20:
            recommendations.append(
                "High dependency count - review and remove unused imports"
            )

        if decay_score >= 70:
            recommendations.append(
                "CRITICAL: Schedule refactoring within next sprint"
            )
        elif decay_score >= 50:
            recommendations.append(
                "Add to technical debt backlog for next quarter"
            )

        return recommendations

    def train(self, X, y):
        """Train the model (for future use)"""
        if not SKLEARN_AVAILABLE or self.model is None:
            return
        self.model.fit(X, y)
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model trained and saved to {self.model_path}")
