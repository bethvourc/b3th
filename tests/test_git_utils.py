"""
Unit tests for b3th.git_utils helpers, including merge-conflict detection.
"""

import subprocess
from pathlib import Path

from b3th import git_utils


# ────────────────────────────────────────────────────────────────────────────────
# Helper to bootstrap a throw-away repo
# ────────────────────────────────────────────────────────────────────────────────
def _init_repo(repo: Path) -> None:
    """Initialise a bare-bones repository with user identity configured."""
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)  # noqa: S603,S607
    subprocess.run(
        ["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True
    )  # noqa: S603,S607
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)  # noqa: S603,S607


# ────────────────────────────────────────────────────────────────────────────────
# Smoke-test: basic helpers
# ────────────────────────────────────────────────────────────────────────────────
def test_git_utils_end_to_end(tmp_path: Path) -> None:
    """
    Create a temp repo, stage a file, and ensure core helper functions behave.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)

    # Create and stage a file
    sample = repo / "sample.txt"
    sample.write_text("hello\n")
    subprocess.run(["git", "add", "sample.txt"], cwd=repo, check=True)  # noqa: S603,S607

    # Assertions
    assert git_utils.is_git_repo(repo) is True

    branch = git_utils.get_current_branch(repo)
    # Git 2.28+ defaults to 'main'; older versions use 'master'
    assert branch in {"main", "master"}

    diff = git_utils.get_staged_diff(repo)
    assert "+hello" in diff  # diff should include added line


# ────────────────────────────────────────────────────────────────────────────────
# Merge-conflict detection tests
# ────────────────────────────────────────────────────────────────────────────────
def test_no_conflicts(tmp_path: Path) -> None:
    """Clean repo → has_merge_conflicts() should return False."""
    _init_repo(tmp_path)

    (tmp_path / "a.txt").write_text("content\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)  # noqa: S603,S607
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)  # noqa: S603,S607

    assert git_utils.has_merge_conflicts(tmp_path) is False


def test_detect_conflicts(tmp_path: Path) -> None:
    """Create diverging branches and verify conflict markers are detected."""
    _init_repo(tmp_path)

    # Capture whatever the repo's default branch is (main or master)
    default_branch = git_utils.get_current_branch(tmp_path)

    # Commit on default branch
    (tmp_path / "file.txt").write_text("line-1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)  # noqa: S603,S607
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True)  # noqa: S603,S607

    # Create feature branch with conflicting edit
    subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=tmp_path, check=True)  # noqa: S603,S607
    (tmp_path / "file.txt").write_text("feature change\n")
    subprocess.run(["git", "commit", "-am", "feature edit"], cwd=tmp_path, check=True)  # noqa: S603,S607

    # Switch back to the original default branch
    subprocess.run(["git", "checkout", "-q", default_branch], cwd=tmp_path, check=True)  # noqa: S603,S607
    (tmp_path / "file.txt").write_text("main change\n")
    subprocess.run(["git", "commit", "-am", "main edit"], cwd=tmp_path, check=True)  # noqa: S603,S607

    # Attempt merge (will leave conflicts)
    subprocess.run(["git", "merge", "-q", "feature"], cwd=tmp_path)  # noqa: S603,S607

    assert git_utils.has_merge_conflicts(tmp_path) is True
