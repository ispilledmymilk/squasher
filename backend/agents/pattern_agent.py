# backend/agents/pattern_agent.py

import os
from typing import Any, Dict

from .base_agent import BaseAgent
from ml.pattern_matcher import PatternMatcher
from utils.config import config
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI

    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    LANGCHAIN_OPENAI_AVAILABLE = False


class PatternAgent(BaseAgent):
    """Agent 4: RAG pattern match + optional OpenAI code review (blueprint)."""

    def __init__(self):
        super().__init__("PatternAgent")
        self._matcher = PatternMatcher()

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Find similar decay patterns and optional LLM risk summary."""
        file_path = context.get("file_path")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[:1000]
                code_sample = "".join(lines)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return {"agent": self.name, "status": "error"}

        similar_patterns = self._matcher.match_decay(code_sample, n=5)
        similar_bugs = self._matcher.match_bugs(code_sample, n=3)

        pattern_risk = self._calculate_pattern_risk(
            similar_patterns, similar_bugs
        )

        result: Dict[str, Any] = {
            "agent": self.name,
            "pattern_matches": len(similar_patterns["ids"][0]),
            "bug_pattern_matches": len(similar_bugs["ids"][0]),
            "pattern_risk_score": pattern_risk,
            "similar_issues": self._extract_similar_issues(
                similar_patterns, similar_bugs
            ),
            "warnings": self._generate_warnings(similar_bugs),
        }

        llm_extra = self._maybe_llm_review(code_sample)
        result.update(llm_extra)
        if llm_extra.get("llm_pattern_summary") and llm_extra.get("llm_used"):
            result["warnings"] = list(result["warnings"]) + [
                "LLM review: see llm_pattern_summary for narrative risks."
            ]

        self.log_result(result)
        return result

    def _maybe_llm_review(self, code_sample: str) -> Dict[str, Any]:
        if not config.OPENAI_API_KEY or not LANGCHAIN_OPENAI_AVAILABLE:
            return {"llm_used": False}

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        try:
            llm = ChatOpenAI(
                model=model,
                api_key=config.OPENAI_API_KEY,
                temperature=0,
            )
            excerpt = code_sample[:8000]
            prompt = (
                "You are a staff engineer reviewing code for future bugs and "
                "technical debt. Given the excerpt below, respond with 3-5 short "
                "bullet lines (prefix with - ). Focus on maintainability, edge "
                "cases, and patterns that often cause production incidents. "
                "If the snippet is too small, say so in one line.\n\n```\n"
                f"{excerpt}\n```"
            )
            out = llm.invoke([HumanMessage(content=prompt)])
            text = (getattr(out, "content", None) or str(out)).strip()
            return {
                "llm_used": True,
                "llm_model": model,
                "llm_pattern_summary": text,
            }
        except Exception as e:
            logger.warning("LLM pattern review failed: %s", e)
            return {"llm_used": False, "llm_error": str(e)}

    def _calculate_pattern_risk(
        self, decay_patterns: Dict, bug_patterns: Dict
    ) -> float:
        """Calculate risk based on pattern similarity"""
        risk_score = 0.0

        decay_distances = decay_patterns.get("distances", [[]])
        if decay_distances and decay_distances[0]:
            for distance in decay_distances[0]:
                similarity = 1 - min(float(distance), 1.0)
                risk_score += similarity * 20

        bug_distances = bug_patterns.get("distances", [[]])
        if bug_distances and bug_distances[0]:
            for distance in bug_distances[0]:
                similarity = 1 - min(float(distance), 1.0)
                risk_score += similarity * 30

        return min(100, risk_score)

    def _extract_similar_issues(
        self, decay_patterns: Dict, bug_patterns: Dict
    ) -> list:
        """Extract issues from similar patterns"""
        issues = []

        bug_metas = bug_patterns.get("metadatas", [[]])
        if bug_metas and bug_metas[0]:
            for metadata in bug_metas[0][:3]:
                bug_type = metadata.get("bug_type", "unknown")
                severity = metadata.get("severity", "unknown")
                issues.append(
                    {
                        "type": bug_type,
                        "severity": severity,
                        "source": "historical_bug_pattern",
                    }
                )

        return issues

    def _generate_warnings(self, bug_patterns: Dict) -> list:
        """Generate warnings based on bug patterns"""
        warnings = []

        bug_ids = bug_patterns.get("ids", [[]])
        if bug_ids and bug_ids[0]:
            match_count = len(bug_ids[0])
            warnings.append(
                f"Similar to {match_count} known bug patterns."
            )
            bug_metas = bug_patterns.get("metadatas", [[]])
            if bug_metas and bug_metas[0]:
                for metadata in bug_metas[0]:
                    if metadata.get("severity") == "critical":
                        warnings.append(
                            "Matches critical bug pattern - immediate review recommended."
                        )
                        break

        return warnings
