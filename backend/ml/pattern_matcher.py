# backend/ml/pattern_matcher.py
"""RAG pattern matching facade over Chroma (blueprint module)."""

from __future__ import annotations

from typing import Any, Dict

from data.vector_store import VectorStore


class PatternMatcher:
    """Query decay and bug pattern collections for a code snippet."""

    def __init__(self, store: VectorStore | None = None):
        self._store = store or VectorStore()

    def match_decay(self, code_snippet: str, n: int = 5) -> Dict[str, Any]:
        return self._store.find_similar_patterns(code_snippet, n_results=n)

    def match_bugs(self, code_snippet: str, n: int = 5) -> Dict[str, Any]:
        return self._store.find_bug_patterns(code_snippet, n_results=n)
