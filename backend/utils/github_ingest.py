# backend/utils/github_ingest.py
"""
Parse GitHub HTTPS URLs, shallow-clone repositories, or fetch a single raw file.
Restricted to github.com / raw.githubusercontent.com to reduce SSRF risk.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from utils.config import config
from utils.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class ParsedGithub:
    owner: str
    repo: str
    ref: Optional[str]
    """Branch or tag from URL, if present."""
    path_in_repo: Optional[str]
    """File or directory path inside the repo, if present (blob/tree/raw)."""
    is_raw_file: bool
    """True if the URL points at raw.githubusercontent.com (single file fetch)."""


def _strip_git_suffix(name: str) -> str:
    return name[:-4] if name.endswith(".git") else name


def _validate_host(hostname: str) -> str:
    h = hostname.lower().strip(".")
    if h == "www.github.com":
        h = "github.com"
    if h not in ("github.com", "raw.githubusercontent.com"):
        raise ValueError(f"Host not allowed: {hostname}")
    return h


def parse_github_url(url: str) -> ParsedGithub:
    """Parse a GitHub repo, blob, tree, or raw content URL."""
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL is empty")
    parsed = urlparse(raw)
    if parsed.scheme != "https":
        raise ValueError("Only https:// GitHub URLs are supported")
    host = _validate_host(parsed.netloc.split("@")[-1])
    parts = [p for p in parsed.path.split("/") if p]
    if host == "github.com":
        if len(parts) < 2:
            raise ValueError("Expected https://github.com/owner/repo[/...]")
        owner, repo = parts[0], _strip_git_suffix(parts[1])
        ref: Optional[str] = None
        path_in_repo: Optional[str] = None
        if len(parts) > 2:
            kind = parts[2]
            if kind in ("blob", "tree") and len(parts) >= 4:
                ref = parts[3]
                path_in_repo = "/".join(parts[4:]) if len(parts) > 4 else None
            elif kind not in ("blob", "tree", "issues", "pull", "discussions"):
                # e.g. /owner/repo without blob — still valid repo root
                pass
        return ParsedGithub(
            owner=owner,
            repo=repo,
            ref=ref,
            path_in_repo=path_in_repo,
            is_raw_file=False,
        )
    # raw.githubusercontent.com
    if len(parts) < 4:
        raise ValueError(
            "Expected https://raw.githubusercontent.com/owner/repo/ref/path/to/file"
        )
    owner, repo, ref = parts[0], _strip_git_suffix(parts[1]), parts[2]
    path_in_repo = "/".join(parts[3:])
    return ParsedGithub(
        owner=owner,
        repo=repo,
        ref=ref,
        path_in_repo=path_in_repo,
        is_raw_file=True,
    )


def _clone_url(owner: str, repo: str) -> str:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        return f"https://{token}@github.com/{owner}/{repo}.git"
    return f"https://github.com/{owner}/{repo}.git"


def _run_git(args: List[str], cwd: Optional[str] = None) -> None:
    timeout = config.GITHUB_CLONE_TIMEOUT_SEC
    r = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "").strip() or "git failed"
        logger.warning("git %s failed: %s", " ".join(args[:4]), err[:500])
        raise RuntimeError(err[:2000])


def shallow_clone(
    owner: str,
    repo: str,
    dest: Path,
    ref: Optional[str] = None,
) -> None:
    """Shallow clone default or given branch/tag into dest (empty dir)."""
    url = _clone_url(owner, repo)
    dest.mkdir(parents=True, exist_ok=True)
    if ref:
        cmd = ["git", "clone", "--depth", "1", "--branch", ref, url, str(dest)]
    else:
        cmd = ["git", "clone", "--depth", "1", url, str(dest)]
    try:
        _run_git(cmd)
    except RuntimeError:
        if ref:
            _run_git(["git", "clone", "--depth", "1", url, str(dest)])
        else:
            raise


def _init_minimal_git_repo(repo_dir: Path) -> None:
    """Create a single-commit repo so GitPython-based agents can run on raw downloads."""
    _run_git(["git", "init"], cwd=str(repo_dir))
    _run_git(
        ["git", "config", "user.email", "codedecay@local"],
        cwd=str(repo_dir),
    )
    _run_git(["git", "config", "user.name", "codedecay"], cwd=str(repo_dir))
    _run_git(["git", "add", "-A"], cwd=str(repo_dir))
    _run_git(["git", "commit", "-m", "init", "--allow-empty"], cwd=str(repo_dir))


def fetch_raw_file(owner: str, repo: str, ref: str, path_in_repo: str, dest_file: Path) -> None:
    """Download a single file from raw.githubusercontent.com."""
    path_in_repo = path_in_repo.lstrip("/")
    raw_url = (
        f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path_in_repo}"
    )
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=float(config.GITHUB_CLONE_TIMEOUT_SEC)) as client:
        r = client.get(raw_url, follow_redirects=True)
        r.raise_for_status()
        dest_file.write_bytes(r.content)


@dataclass
class GithubWorkdir:
    """Temporary checkout; call cleanup() when done."""

    root: str
    """Directory used as repo_path (contains .git for clones, or a single file)."""
    cleanup: Callable[[], None]


def prepare_github_workdir(
    url: str,
    ref_override: Optional[str] = None,
) -> Tuple[ParsedGithub, GithubWorkdir]:
    """
    Clone repo or download one raw file into a unique cache directory.
    Returns (parsed metadata, workdir with cleanup).
    """
    parsed = parse_github_url(url)
    session_id = uuid.uuid4().hex[:12]
    base = Path(config.GITHUB_CACHE_DIR) / session_id
    base.mkdir(parents=True, exist_ok=True)

    def cleanup() -> None:
        try:
            shutil.rmtree(base, ignore_errors=True)
        except OSError:
            pass

    if parsed.is_raw_file:
        if not parsed.path_in_repo:
            cleanup()
            raise ValueError("Raw URL must include a file path")
        ref = ref_override or parsed.ref
        if not ref:
            cleanup()
            raise ValueError("Raw URL must include a ref (branch/tag/commit)")
        safe_name = Path(parsed.path_in_repo).name
        if not safe_name or ".." in parsed.path_in_repo:
            cleanup()
            raise ValueError("Invalid file path in URL")
        out_file = base / safe_name
        try:
            fetch_raw_file(
                parsed.owner,
                parsed.repo,
                ref,
                parsed.path_in_repo,
                out_file,
            )
        except Exception:
            cleanup()
            raise
        try:
            _init_minimal_git_repo(base)
        except Exception:
            cleanup()
            raise
        return parsed, GithubWorkdir(root=str(base), cleanup=cleanup)

    ref = ref_override or parsed.ref
    clone_dest = base / "repo"
    try:
        shallow_clone(parsed.owner, parsed.repo, clone_dest, ref=ref)
    except Exception:
        cleanup()
        raise
    repo_root = str(clone_dest)
    return parsed, GithubWorkdir(root=repo_root, cleanup=cleanup)


def list_analyzable_files(
    repo_root: str,
    extensions: List[str],
    focus_path: Optional[str] = None,
    walk_root: Optional[str] = None,
) -> List[str]:
    """
    Walk repo for files with given extensions, respecting size limits.
    If focus_path is set and is a file inside the repo, return it first
    (still subject to max file count elsewhere).
    If walk_root is set (e.g. GitHub tree URL), only walk under that directory.
    """
    skip_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
    out: List[str] = []
    rr = os.path.realpath(repo_root)
    scan_root = os.path.realpath(walk_root) if walk_root else rr
    if not (scan_root == rr or scan_root.startswith(rr + os.sep)):
        scan_root = rr

    focus_full: Optional[str] = None
    if focus_path:
        cand = os.path.normpath(os.path.join(repo_root, focus_path))
        cr = os.path.realpath(cand)
        if (cr == rr or cr.startswith(rr + os.sep)) and os.path.isfile(cr):
            focus_full = cr

    if focus_full and os.path.getsize(focus_full) <= config.MAX_FILE_BYTES_FOR_SCAN:
        out.append(focus_full)

    for root, dirs, files in os.walk(scan_root):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for name in files:
            path = os.path.join(root, name)
            if focus_full and os.path.realpath(path) == os.path.realpath(focus_full):
                continue
            if not any(name.endswith(ext) for ext in extensions):
                continue
            try:
                if os.path.getsize(path) > config.MAX_FILE_BYTES_FOR_SCAN:
                    continue
            except OSError:
                continue
            out.append(path)
    return out


def repo_collaboration_hints(repo_root: str) -> dict:
    """Lightweight checks that help sharing and onboarding."""
    root = Path(repo_root)
    names = {p.name.lower() for p in root.iterdir()} if root.is_dir() else set()
    readme = any(
        n.startswith("readme.") or n == "readme"
        for n in names
    )
    license_ok = any(
        n.startswith("license") or n == "copying"
        for n in names
    )
    gitignore = ".gitignore" in names
    contributing = any(n.startswith("contributing") for n in names)
    code_of_conduct = any(
        "code_of_conduct" in n or n == "conduct.md"
        for n in names
    )
    return {
        "has_readme": readme,
        "has_license": license_ok,
        "has_gitignore": gitignore,
        "has_contributing": contributing,
        "has_code_of_conduct": code_of_conduct,
    }
