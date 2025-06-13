"""
Low-level helpers for interacting with Git.

These utilities are deliberately minimal and shell out to the local `git`
binary so that higher-level code can stay Python-only.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


class GitError(RuntimeError):
    """Raised when an underlying git command fails."""


def _run_git(args: List[str], cwd: Path | str | None = None) -> str:
    """Run `git <args>` and return stdout, raising GitError on failure."""
    result = subprocess.run(  # noqa: S603,S607 (trusted local call)
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


# Public helpers -----------------------------------------------------------


def is_git_repo(path: Path | str = ".") -> bool:
    """Return True if *path* is inside a Git working tree."""
    try:
        _run_git(["rev-parse", "--is-inside-work-tree"], cwd=path)
        return True
    except GitError:
        return False


def get_current_branch(path: Path | str = ".") -> str:
    """
    Return the current branch name for *path*.

    Works even on a freshly-initialized repository that has no commits yet by
    using `git symbolic-ref`. If HEAD is detached, fall back to the abbreviated
    commit hash.
    """
    try:
        # Succeeds even before the first commit
        return _run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=path)
    except GitError:
        # Detached HEAD: return the short commit hash instead
        return _run_git(["rev-parse", "--short", "HEAD"], cwd=path)


def get_staged_diff(path: Path | str = ".") -> str:
    """
    Return the unified diff of **staged** changes (index vs HEAD).
    An empty string means nothing is currently staged.
    """
    return _run_git(["diff", "--staged"], cwd=path)
