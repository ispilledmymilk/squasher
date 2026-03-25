"""Tests for blueprint analyzer modules."""

from analyzers.complexity_calculator import ComplexityCalculator
from analyzers.change_frequency import file_change_stats


def test_complexity_calculator_python_snippet():
    code = """
def foo(a, b):
    if a:
        return b
    return 0
"""
    cc = ComplexityCalculator.cyclomatic_complexity_python(code)
    assert cc >= 1.0
    loc = ComplexityCalculator.count_loc(code)
    assert loc > 0


def test_change_frequency_empty_git(tmp_path):
    import subprocess

    r = subprocess.run(
        ["git", "init"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    if r.returncode != 0:
        import pytest

        pytest.skip(f"git init unavailable: {r.stderr.decode()[:120]}")
    f = tmp_path / "m.py"
    f.write_text("x = 1\n")
    stats = file_change_stats(str(tmp_path), str(f))
    assert "change_frequency" in stats
