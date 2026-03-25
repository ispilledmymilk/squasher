# backend/agents/code_style_agent.py
"""
Detects bug-prone code style and patterns common in AI-generated code.
Used to flag issues before commit/push.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

from .base_agent import BaseAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)

# File extensions we can analyze for style
STYLE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb"}


class CodeStyleAgent(BaseAgent):
    """
    Agent 5: Detects bug-prone style and AI-like code patterns.
    Surfaces issues that could cause bugs after commit/push.
    """

    def __init__(self):
        super().__init__("CodeStyleAgent")

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze file for style-based and AI-style issues."""
        file_path = context.get("file_path")
        ext = Path(file_path).suffix

        if ext not in STYLE_EXTENSIONS:
            return {"agent": self.name, "issues": [], "risk_score": 0, "warnings": []}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return {"agent": self.name, "issues": [], "risk_score": 0, "warnings": []}

        issues: List[Dict[str, Any]] = []

        # Bug-prone style checks (language-agnostic or Python/JS)
        issues.extend(self._check_bare_except(content, lines, ext))
        issues.extend(self._check_empty_catch(content, lines, ext))
        issues.extend(self._check_placeholder_comments(content, lines))
        issues.extend(self._check_magic_numbers(content, lines))
        issues.extend(self._check_broad_except(content, lines, ext))
        issues.extend(self._check_missing_validation(content, lines, ext))
        issues.extend(self._check_hardcoded_secrets(content, lines))

        # AI-style / generic patterns that often lead to bugs
        issues.extend(self._check_ai_style_comment_ratio(content, lines))
        issues.extend(self._check_placeholder_todos(content, lines))
        issues.extend(self._check_generic_names(content, lines, ext))
        issues.extend(self._check_copy_paste_blocks(lines, ext))

        risk_score = self._issues_to_risk_score(issues)
        warnings = self._issues_to_warnings(issues)

        result = {
            "agent": self.name,
            "issues": issues,
            "issue_count": len(issues),
            "risk_score": min(100, risk_score),
            "warnings": warnings,
        }
        self.log_result(result)
        return result

    def _check_bare_except(self, content: str, lines: List[str], ext: str) -> List[Dict]:
        out = []
        if ext != ".py":
            return out
        # except: or except Exception: without handling
        for i, line in enumerate(lines):
            if re.search(r"\bexcept\s*:", line) and "pass" not in line and "#" not in line:
                out.append({
                    "type": "bare_except",
                    "severity": "high",
                    "line": i + 1,
                    "message": "Bare 'except:' catches everything and can hide bugs. Use 'except Exception:' or specific exception.",
                    "category": "bug_prone_style",
                })
        return out

    def _check_empty_catch(self, content: str, lines: List[str], ext: str) -> List[Dict]:
        out = []
        if ext not in (".py", ".js", ".ts"):
            return out
        for i, line in enumerate(lines):
            if ext == ".py" and re.match(r"except\s+.*:\s*$", line.strip()) and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line in ("pass", "") or next_line.startswith("#"):
                    out.append({
                        "type": "empty_except",
                        "severity": "medium",
                        "line": i + 2,
                        "message": "Empty or pass-only except block hides errors. Log or re-raise.",
                        "category": "bug_prone_style",
                    })
            elif ext in (".js", ".ts") and "catch" in line and "{}" in line:
                out.append({
                    "type": "empty_catch",
                    "severity": "medium",
                    "line": i + 1,
                    "message": "Empty catch block hides errors. Log or handle.",
                    "category": "bug_prone_style",
                })
        return out

    def _check_placeholder_comments(self, content: str, lines: List[str]) -> List[Dict]:
        out = []
        placeholders = [
            (r"\bTODO\b", "TODO"),
            (r"\bFIXME\b", "FIXME"),
            (r"\bXXX\b", "XXX"),
            (r"\bHACK\b", "HACK"),
            (r"placeholder", "placeholder"),
            (r"implement\s+later", "implement later"),
            (r"not\s+implemented", "not implemented"),
        ]
        for i, line in enumerate(lines):
            for pattern, name in placeholders:
                if re.search(pattern, line, re.I):
                    out.append({
                        "type": "placeholder_comment",
                        "severity": "low",
                        "line": i + 1,
                        "message": f"'{name}' left in code. Fix before commit to avoid incomplete behavior.",
                        "category": "ai_style",
                    })
                    break
        return out

    def _check_magic_numbers(self, content: str, lines: List[str]) -> List[Dict]:
        out = []
        # Numbers that look like magic (not 0, 1, -1, 2, 100, 1000)
        magic = re.finditer(r"\b(?:[2-9]|[1-9]\d{2,})\b", content)
        count = 0
        for m in magic:
            count += 1
            if count > 5:  # Only flag if many
                break
        if count >= 5:
            out.append({
                "type": "magic_numbers",
                "severity": "low",
                "line": 0,
                "message": "Many literal numbers in code. Consider named constants to avoid bugs when changing values.",
                "category": "bug_prone_style",
            })
        return out

    def _check_broad_except(self, content: str, lines: List[str], ext: str) -> List[Dict]:
        out = []
        if ext != ".py":
            return out
        if re.search(r"except\s+Exception\s*:", content) and "pass" in content:
            out.append({
                "type": "broad_except_pass",
                "severity": "medium",
                "line": 0,
                "message": "Catching Exception and passing can hide real bugs. Prefer specific exceptions or log.",
                "category": "bug_prone_style",
            })
        return out

    def _check_missing_validation(self, content: str, lines: List[str], ext: str) -> List[Dict]:
        out = []
        # Python: def foo(x): without any if not x / isinstance / etc. in next ~5 lines
        if ext == ".py":
            for i, line in enumerate(lines):
                m = re.match(r"def\s+\w+\s*\([^)]*\)\s*:", line)
                if m and "self" not in m.group(0):
                    params = re.findall(r"def\s+\w+\s*\(([^)]*)\)", line)
                    if params and params[0].strip() and "=" not in params[0]:
                        # Could add: check next N lines for validation
                        pass  # Keep simple for now
        # Generic: division by variable without check
        if "/" in content or "//" in content:
            if "if" not in content and "?" not in content and "guard" not in content.lower():
                pass  # Heuristic only
        return out

    def _check_hardcoded_secrets(self, content: str, lines: List[str]) -> List[Dict]:
        out = []
        secret_patterns = [
            (r"password\s*=\s*['\"][^'\"]+['\"]", "hardcoded password"),
            (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "hardcoded API key"),
            (r"secret\s*=\s*['\"][^'\"]+['\"]", "hardcoded secret"),
            (r"Bearer\s+[a-zA-Z0-9_\-\.]+", "hardcoded Bearer token"),
        ]
        for i, line in enumerate(lines):
            for pattern, desc in secret_patterns:
                if re.search(pattern, line, re.I):
                    out.append({
                        "type": "hardcoded_secret",
                        "severity": "critical",
                        "line": i + 1,
                        "message": f"Possible {desc}. Use environment variables or a secrets manager before commit.",
                        "category": "bug_prone_style",
                    })
                    break
        return out

    def _check_ai_style_comment_ratio(self, content: str, lines: List[str]) -> List[Dict]:
        out = []
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        comment_lines = [l for l in lines if l.strip().startswith("#") or "//" in l]
        if len(code_lines) < 10:
            return out
        ratio = len(comment_lines) / max(len(code_lines), 1)
        if ratio > 0.6:
            out.append({
                "type": "high_comment_ratio",
                "severity": "low",
                "line": 0,
                "message": "Very high comment-to-code ratio. Common in AI-generated code; ensure logic is correct and comments are accurate.",
                "category": "ai_style",
            })
        return out

    def _check_placeholder_todos(self, content: str, lines: List[str]) -> List[Dict]:
        return self._check_placeholder_comments(content, lines)  # Reuse

    def _check_generic_names(self, content: str, lines: List[str], ext: str) -> List[Dict]:
        out = []
        generic = [
            r"\bdata\s*=",
            r"\bresult\s*=",
            r"\bvalue\s*=",
            r"\bthing\s*=",
            r"\bstuff\s*=",
            r"def\s+process\s*\(",
            r"def\s+handle\s*\(",
            r"def\s+do_something\s*\(",
        ]
        count = sum(1 for p in generic if re.search(p, content))
        if count >= 4:
            out.append({
                "type": "generic_names",
                "severity": "low",
                "line": 0,
                "message": "Many generic names (data, result, process). Consider descriptive names to avoid confusion and bugs.",
                "category": "ai_style",
            })
        return out

    def _check_copy_paste_blocks(self, lines: List[str], ext: str) -> List[Dict]:
        out = []
        # Very similar consecutive lines (simplified: same line repeated)
        for i in range(len(lines) - 2):
            a, b = lines[i].strip(), lines[i + 1].strip()
            if a and b and a == b and len(a) > 20:
                out.append({
                    "type": "duplicate_lines",
                    "severity": "medium",
                    "line": i + 1,
                    "message": "Duplicate consecutive lines. May be copy-paste; verify logic.",
                    "category": "bug_prone_style",
                })
        return out

    def _issues_to_risk_score(self, issues: List[Dict]) -> float:
        score = 0.0
        for i in issues:
            sev = i.get("severity", "low")
            if sev == "critical":
                score += 25
            elif sev == "high":
                score += 15
            elif sev == "medium":
                score += 8
            else:
                score += 3
        return score

    def _issues_to_warnings(self, issues: List[Dict]) -> List[str]:
        return [i["message"] for i in issues[:10]]
