# backend/ml/model_trainer.py
"""Train / persist decay RandomForest (blueprint training pipeline)."""

from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple

import numpy as np
from utils.config import config
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import joblib
    from sklearn.ensemble import RandomForestRegressor

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def _default_model_path() -> str:
    return os.path.join(config.MODEL_PATH, "decay_model.pkl")


def train_random_forest_regressor(
    X: np.ndarray,
    y: np.ndarray,
    n_estimators: int = 100,
    max_depth: int = 10,
    random_state: int = 42,
    model_path: Optional[str] = None,
) -> Tuple[Any, str]:
    """
    Fit RandomForestRegressor on feature matrix X and target y; save with joblib.
    Returns (model, path_written).
    """
    if not SKLEARN_AVAILABLE:
        raise RuntimeError("scikit-learn and joblib are required for training")

    if X.size == 0 or len(y) == 0:
        raise ValueError("X and y must be non-empty")

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
    )
    model.fit(X, y)
    out = model_path or _default_model_path()
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    joblib.dump(model, out)
    logger.info("Saved decay model to %s", out)
    return model, out


def synthetic_training_pair(
    n_samples: int = 50,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic (X, y) for smoke-testing the training path when no DB history exists.
    Features: complexity, velocity-ish, imports, pattern hits (8 dims — matches DecayPredictor._extract_features).
    """
    rng = np.random.default_rng(seed)
    X = rng.random((n_samples, 8)) * 100
    y = rng.random(n_samples) * 100
    return X, y


def train_and_save_default_synthetic() -> str:
    """Convenience for scripts: train on synthetic data and return model path."""
    X, y = synthetic_training_pair()
    _, path = train_random_forest_regressor(X, y)
    return path
