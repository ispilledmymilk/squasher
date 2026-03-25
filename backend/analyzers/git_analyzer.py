# backend/analyzers/git_analyzer.py

import os
from datetime import datetime, timedelta
from typing import Dict, List
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from git import Repo
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False


class GitAnalyzer:
    """Analyze Git history for change patterns"""

    def __init__(self, repo_path: str):
        if not GITPYTHON_AVAILABLE:
            raise ImportError("GitPython is required. pip install gitpython")
        try:
            self.repo = Repo(repo_path)
            logger.info(f"Git repository loaded: {repo_path}")
        except Exception as e:
            logger.error(f"Error loading git repository: {e}")
            raise

    def analyze_file_history(
        self,
        file_path: str,
        days_back: int = 90,
    ) -> Dict:
        """Analyze change history for a file"""
        try:
            since_date = datetime.now() - timedelta(days=days_back)

            # Path relative to repo root for iter_commits
            try:
                if self.repo.working_dir and os.path.isabs(file_path):
                    rel_path = os.path.relpath(
                        file_path, self.repo.working_dir
                    ).replace("\\", "/")
                else:
                    rel_path = file_path.replace("\\", "/")
            except Exception:
                rel_path = file_path

            commits = list(
                self.repo.iter_commits(paths=rel_path, since=since_date)
            )

            authors = set()
            commit_dates = []

            for commit in commits:
                authors.add(commit.author.email)
                commit_dates.append(commit.committed_datetime)

            change_frequency = len(commits)
            authors_count = len(authors)

            if len(commit_dates) > 1:
                commit_dates.sort()
                time_diffs = [
                    (commit_dates[i + 1] - commit_dates[i]).days
                    for i in range(len(commit_dates) - 1)
                ]
                avg_days_between_changes = sum(time_diffs) / len(time_diffs)
            else:
                avg_days_between_changes = float(days_back)

            return {
                "change_frequency": change_frequency,
                "authors_count": authors_count,
                "avg_days_between_changes": round(avg_days_between_changes, 2),
                "last_modified": commit_dates[0] if commit_dates else None,
            }

        except Exception as e:
            logger.error(f"Error analyzing git history for {file_path}: {e}")
            return {
                "change_frequency": 0,
                "authors_count": 0,
                "avg_days_between_changes": 0,
                "last_modified": None,
            }

    def get_recent_changed_files(self, days_back: int = 30) -> List[str]:
        """Get list of recently changed files"""
        try:
            since_date = datetime.now() - timedelta(days=days_back)
            commits = list(self.repo.iter_commits(since=since_date))
            changed_files = set()
            for commit in commits:
                for item in commit.stats.files:
                    changed_files.add(item)
            return list(changed_files)
        except Exception as e:
            logger.error(f"Error getting recent changed files: {e}")
            return []
