"""
Unit tests for b3th.stats.get_stats()

All Git calls are stubbed so no real repository is needed.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import List

from b3th import stats as st


def _fake_run_git_factory(commit_log: str, numstat: str):
    """
    Returns a stub function that mimics git-utils.run_git.

    It looks at the args:
        • '--pretty=%h'  -> commit_log
        • '--numstat'    -> numstat
    """
    def _fake_run_git(args: List[str], cwd=None):  # noqa: ANN001
        if "--pretty=%h" in args:
            return commit_log
        if "--numstat" in args:
            return numstat
        return ""
    return _fake_run_git


def test_stats_counts(monkeypatch, tmp_path: Path):
    """
    Two commits touching two files with insertions/deletions.
    """
    commit_log = "abc123\n def456\n"
    numstat = "10\t0\tfoo.py\n5\t2\tbar.py\n-\t-\tbinary.png\n"

    monkeypatch.setattr(st, "is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr(
        st, "run_git", _fake_run_git_factory(commit_log, numstat), raising=True
    )

    result = st.get_stats(tmp_path, last="7d")
    assert result == {"commits": 2, "files": 2, "additions": 15, "deletions": 2}


def test_stats_no_commits(monkeypatch, tmp_path: Path):
    """When git log returns nothing, all counts should be zero."""
    monkeypatch.setattr(st, "is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr(
        st, "run_git", _fake_run_git_factory("", ""), raising=True
    )

    result = st.get_stats(tmp_path, last="7d")
    assert result == {"commits": 0, "files": 0, "additions": 0, "deletions": 0}
