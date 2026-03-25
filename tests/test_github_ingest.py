"""Unit tests for GitHub URL parsing (no network)."""

import pytest

from utils.github_ingest import parse_github_url


def test_parse_repo_root():
    p = parse_github_url("https://github.com/octocat/Hello-World")
    assert p.owner == "octocat"
    assert p.repo == "Hello-World"
    assert p.ref is None
    assert p.path_in_repo is None
    assert p.is_raw_file is False


def test_parse_blob():
    p = parse_github_url(
        "https://github.com/octocat/Hello-World/blob/main/README"
    )
    assert p.owner == "octocat"
    assert p.repo == "Hello-World"
    assert p.ref == "main"
    assert p.path_in_repo == "README"
    assert p.is_raw_file is False


def test_parse_raw():
    p = parse_github_url(
        "https://raw.githubusercontent.com/octocat/Hello-World/v1.0/README.md"
    )
    assert p.owner == "octocat"
    assert p.repo == "Hello-World"
    assert p.ref == "v1.0"
    assert p.path_in_repo == "README.md"
    assert p.is_raw_file is True


def test_reject_non_https():
    with pytest.raises(ValueError, match="https"):
        parse_github_url("http://github.com/a/b")


def test_reject_bad_host():
    with pytest.raises(ValueError, match="not allowed"):
        parse_github_url("https://evil.com/a/b")
