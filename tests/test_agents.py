"""Smoke tests for agents (no OpenAI)."""

import subprocess

import pytest


@pytest.fixture
def tiny_git_repo(tmp_path):
    import pytest

    r = subprocess.run(
        ["git", "init"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    if r.returncode != 0:
        pytest.skip(f"git init unavailable: {r.stderr.decode()[:120]}")
    subprocess.run(
        ["git", "config", "user.email", "t@test.local"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    f = tmp_path / "mod.py"
    f.write_text("def add(a, b):\n    return a + b\n")
    subprocess.run(
        ["git", "add", "mod.py"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    return tmp_path


def test_decay_workflow_file_analyze(tiny_git_repo, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from orchestrator.langgraph_workflow import DecayAnalysisWorkflow

    wf = DecayAnalysisWorkflow(str(tiny_git_repo))
    fp = str(tiny_git_repo / "mod.py")
    out = wf.analyze_file(fp, persist=False)
    assert out.get("status") in ("completed", "error", "unsupported_file")
    if out.get("status") == "completed":
        assert "prediction" in out
        assert "decay_score" in (out.get("prediction") or {})
