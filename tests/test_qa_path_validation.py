"""Tests for production path validation."""
import os
import tempfile

import pytest

from utils.qa_path_validation import (
    validate_file_in_repo,
    validate_file_paths_batch,
    validate_repo_path,
)


def test_validate_repo_path_temp_dir():
    with tempfile.TemporaryDirectory() as d:
        ok, rp = validate_repo_path(d)
        assert ok is True
        assert os.path.isdir(rp)


def test_validate_repo_path_missing():
    ok, msg = validate_repo_path("/nonexistent/path/that/does/not/exist/12345")
    assert ok is False
    assert msg


def test_validate_file_in_repo_inside():
    with tempfile.TemporaryDirectory() as d:
        ok_repo, repo_real = validate_repo_path(d)
        assert ok_repo
        fpath = os.path.join(d, "a.py")
        with open(fpath, "w") as f:
            f.write("x = 1\n")
        ok, fr = validate_file_in_repo(repo_real, fpath)
        assert ok is True
        assert fr and os.path.isfile(fr)


def test_validate_file_outside_repo():
    with tempfile.TemporaryDirectory() as d:
        ok_repo, repo_real = validate_repo_path(d)
        assert ok_repo
    with tempfile.TemporaryDirectory() as other:
        fpath = os.path.join(other, "b.py")
        with open(fpath, "w") as f:
            f.write("y = 2\n")
        ok, fr = validate_file_in_repo(repo_real, fpath)
        assert ok is False


def test_validate_file_paths_batch_truncates():
    with tempfile.TemporaryDirectory() as d:
        ok_repo, repo_real = validate_repo_path(d)
        for i in range(5):
            with open(os.path.join(d, f"f{i}.py"), "w") as f:
                f.write("pass\n")
        paths = [os.path.join(d, f"f{i}.py") for i in range(5)]
        valid, rejected = validate_file_paths_batch(repo_real, paths)
        assert len(valid) <= 5
