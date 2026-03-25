# backend/analyzers/change_frequency.py
"""Git change-frequency helpers (blueprint module; wraps GitAnalyzer)."""

from __future__ import annotations

from typing import Dict, List

from analyzers.git_analyzer import GitAnalyzer
from utils.logger import setup_logger

logger = setup_logger(__name__)


def file_change_stats(
    repo_path: str,
    file_path: str,
    days_back: int = 90,
) -> Dict:
    """Commits, authors, spacing for a file (delegates to GitAnalyzer)."""
    try:
        ga = GitAnalyzer(repo_path)
        return ga.analyze_file_history(file_path, days_back=days_back)
    except Exception as e:
        logger.warning("change_frequency: %s", e)
        return {
            "change_frequency": 0,
            "authors_count": 0,
            "avg_days_between_changes": 0.0,
            "last_modified": None,
        }


def recent_changed_paths(repo_path: str, days_back: int = 30) -> List[str]:
    try:
        return GitAnalyzer(repo_path).get_recent_changed_files(days_back=days_back)
    except Exception as e:
        logger.warning("recent_changed_paths: %s", e)
        return []
