# backend/analyzers/code_analyzer.py

from pathlib import Path
from typing import Dict, Optional

from analyzers.complexity_calculator import ComplexityCalculator
from utils.constants import SUPPORTED_EXTENSIONS
from utils.logger import setup_logger

logger = setup_logger(__name__)

RADON_AVAILABLE = ComplexityCalculator.is_radon_available()


class CodeAnalyzer:
    """Analyze code complexity and maintainability"""

    def analyze_file(self, file_path: str) -> Optional[Dict]:
        """Analyze a single file"""
        try:
            ext = Path(file_path).suffix
            if ext not in SUPPORTED_EXTENSIONS:
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            metrics = {
                "file_path": file_path,
                "lines_of_code": self._count_loc(code),
                "cyclomatic_complexity": self._calculate_complexity(code, ext),
                "maintainability_index": self._calculate_mi(code, ext),
                "comment_ratio": self._calculate_comment_ratio(code),
            }

            return metrics

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return None

    def _count_loc(self, code: str) -> int:
        """Count lines of code"""
        return ComplexityCalculator.count_loc(code)

    def _calculate_complexity(self, code: str, ext: str) -> float:
        """Calculate average cyclomatic complexity"""
        if ext == ".py":
            return ComplexityCalculator.cyclomatic_complexity_python(code)
        return 0.0

    def _calculate_mi(self, code: str, ext: str) -> float:
        """Calculate maintainability index"""
        if ext == ".py":
            return ComplexityCalculator.maintainability_index_python(code)
        return 0.0

    def _calculate_comment_ratio(self, code: str) -> float:
        """Calculate ratio of comments to code"""
        return ComplexityCalculator.comment_ratio(code)
