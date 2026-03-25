# backend/agents/dependency_agent.py

import re
from pathlib import Path
from typing import Any, Dict, Set
from .base_agent import BaseAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DependencyAgent(BaseAgent):
    """Agent 3: Analyzes dependency complexity"""

    def __init__(self):
        super().__init__("DependencyAgent")

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze dependencies for a file"""
        file_path = context.get("file_path")

        imports = self._extract_imports(file_path)
        import_count = len(imports)
        dependency_depth = self._estimate_dependency_depth(imports)
        dependency_risk = self._calculate_dependency_risk(
            import_count, dependency_depth
        )

        result = {
            "agent": self.name,
            "import_count": import_count,
            "dependency_depth": dependency_depth,
            "dependency_risk_score": dependency_risk,
            "imports": list(imports)[:10],
            "warnings": self._generate_warnings(import_count),
        }

        self.log_result(result)
        return result

    def _extract_imports(self, file_path: str) -> Set[str]:
        """Extract import statements from file"""
        imports = set()
        ext = Path(file_path).suffix

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if ext == ".py":
                import_pattern = r"^\s*(?:from|import)\s+([\w\.]+)"
                matches = re.findall(import_pattern, content, re.MULTILINE)
                imports.update(matches)

            elif ext in [".js", ".ts", ".jsx", ".tsx"]:
                import_pattern = r"import\s+.*?from\s+[\'\"]([^\'\"]+)[\'\"]"
                matches = re.findall(import_pattern, content)
                imports.update(matches)

        except Exception as e:
            logger.error(f"Error extracting imports from {file_path}: {e}")

        return imports

    def _estimate_dependency_depth(self, imports: Set[str]) -> int:
        """Estimate maximum dependency depth"""
        if not imports:
            return 0
        return max((imp.count(".") for imp in imports), default=0)

    def _calculate_dependency_risk(
        self, import_count: int, dependency_depth: int
    ) -> float:
        """Calculate dependency risk score (0-100)"""
        risk_score = 0.0

        if import_count > 30:
            risk_score += 30
        elif import_count > 20:
            risk_score += 20
        elif import_count > 10:
            risk_score += 10

        if dependency_depth > 5:
            risk_score += 25
        elif dependency_depth > 3:
            risk_score += 15

        return min(100, risk_score)

    def _generate_warnings(self, import_count: int) -> list:
        """Generate warning messages"""
        warnings = []

        if import_count > 25:
            warnings.append(
                f"Very high import count ({import_count}). Consider modularization."
            )
        elif import_count > 15:
            warnings.append(
                f"High import count ({import_count}). Monitor dependencies."
            )

        return warnings
