# backend/analyzers/complexity_calculator.py
"""Radon-based cyclomatic complexity, maintainability, LOC, comments (blueprint module)."""

from __future__ import annotations

from typing import Optional, Tuple

from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
    from radon.raw import analyze as radon_raw_analyze

    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False


class ComplexityCalculator:
    """Low-level metrics from source text (used by CodeAnalyzer / agents)."""

    @staticmethod
    def is_radon_available() -> bool:
        return RADON_AVAILABLE

    @staticmethod
    def count_loc(code: str) -> int:
        if not RADON_AVAILABLE:
            return len([ln for ln in code.splitlines() if ln.strip()])
        try:
            return radon_raw_analyze(code).loc
        except Exception:
            return len([ln for ln in code.splitlines() if ln.strip()])

    @staticmethod
    def cyclomatic_complexity_python(code: str) -> float:
        if not RADON_AVAILABLE:
            return 0.0
        try:
            blocks = cc_visit(code)
            if not blocks:
                return 0.0
            return round(sum(b.complexity for b in blocks) / len(blocks), 2)
        except Exception:
            return 0.0

    @staticmethod
    def maintainability_index_python(code: str) -> float:
        if not RADON_AVAILABLE:
            return 0.0
        try:
            return round(mi_visit(code, True), 2)
        except Exception:
            return 0.0

    @staticmethod
    def comment_ratio(code: str) -> float:
        if not RADON_AVAILABLE:
            return 0.0
        try:
            raw = radon_raw_analyze(code)
            if raw.loc == 0:
                return 0.0
            return round(raw.comments / raw.loc, 3)
        except Exception:
            return 0.0

    @classmethod
    def metrics_for_python(cls, code: str) -> Tuple[float, float, int, float]:
        """Returns (cc, mi, loc, comment_ratio)."""
        return (
            cls.cyclomatic_complexity_python(code),
            cls.maintainability_index_python(code),
            cls.count_loc(code),
            cls.comment_ratio(code),
        )
