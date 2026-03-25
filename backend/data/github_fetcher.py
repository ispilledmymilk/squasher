# backend/data/github_fetcher.py
"""Fetch GitHub sources for inspection or training pipelines (blueprint module)."""

from __future__ import annotations

from typing import Optional, Tuple

from utils.github_ingest import GithubWorkdir, ParsedGithub, prepare_github_workdir


class GitHubDataFetcher:
    """
    Shallow clone or raw download into a temp directory.
    Caller must invoke workdir.cleanup() when finished.
    """

    def fetch(self, url: str, ref: Optional[str] = None) -> Tuple[ParsedGithub, GithubWorkdir]:
        return prepare_github_workdir(url, ref)
