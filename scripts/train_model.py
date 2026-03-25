#!/usr/bin/env python3
"""Train and save decay RandomForest from synthetic data (bootstrap) or future DB export."""

import os
import sys

# Run from repo root: python scripts/train_model.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ml.model_trainer import train_and_save_default_synthetic  # noqa: E402
from utils.logger import setup_logger  # noqa: E402

logger = setup_logger(__name__)


def main() -> None:
    path = train_and_save_default_synthetic()
    logger.info("Model written to %s", path)
    print(path)


if __name__ == "__main__":
    main()
