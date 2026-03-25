"""
Production-safe path validation for QA API.
Prevents path traversal and ensures analyzed files stay under the repo root.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

from utils.config import config
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _realpath_safe(p: str) -> Optional[str]:
    """Resolve path; return None if missing."""
    try:
        return os.path.realpath(p)
    except OSError:
        return None


def validate_repo_path(repo_path: str) -> Tuple[bool, Optional[str]]:
    """
    Ensure repo_path exists, is a directory, and is not suspiciously short
    (e.g. '/').
    """
    if not repo_path or len(repo_path) > config.MAX_PATH_LENGTH:
        return False, "Invalid repository path"
    rp = _realpath_safe(repo_path)
    if not rp or not os.path.isdir(rp):
        return False, "Repository not found"
    # Disallow analyzing the filesystem root
    if rp == os.path.realpath("/"):
        return False, "Invalid repository path"
    return True, rp


def validate_file_in_repo(repo_real: str, file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Ensure file_path resolves under repo_real (no path traversal).
    Returns (ok, resolved_file_path or error message).
    """
    if not file_path or len(file_path) > config.MAX_PATH_LENGTH:
        return False, None
    fr = _realpath_safe(file_path)
    if not fr:
        return False, None
    if not os.path.isfile(fr):
        return False, None
    repo_prefix = repo_real.rstrip(os.sep) + os.sep
    if not (fr == repo_real or fr.startswith(repo_prefix)):
        return False, None
    return True, fr


def validate_file_paths_batch(
    repo_real: str, file_paths: list
) -> Tuple[list, list]:
    """
    Filter file_paths to those inside repo. Returns (valid_paths, rejected_count).
    """
    valid = []
    rejected = 0
    for fp in file_paths[: config.MAX_PRE_COMMIT_FILES + 1]:
        if len(valid) >= config.MAX_PRE_COMMIT_FILES:
            break
        ok, resolved = validate_file_in_repo(repo_real, fp)
        if ok and resolved:
            if os.path.getsize(resolved) > config.MAX_FILE_BYTES_FOR_SCAN:
                rejected += 1
                logger.warning(f"Skipping oversized file: {resolved}")
                continue
            valid.append(resolved)
        else:
            rejected += 1
    return valid, rejected
