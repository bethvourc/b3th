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



# Internal helper
def _run_git(args: List[str], cwd: Path | str | None = None) -> str:
    """Run `git <args>` and return stdout, raising GitError on failure."""
    result = subprocess.run(                           # noqa: S603,S607
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


# Public convenience wrapper
def run_git(args: List[str], cwd: Path | str | None = None) -> str:
    """
    Public helper that wraps the private _run_git().

    Intended for other modules (stats, summarizer, etc.) that need to run
    arbitrary Git commands without duplicating shell logic.
    """
    return _run_git(args, cwd=cwd)


# Public helpers 
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



# helper: detect unresolved merge conflicts
def has_merge_conflicts(path: Path | str = ".") -> bool:  # pragma: no cover
    """
    Return ``True`` if the working tree under *path* contains any unresolved
    merge conflicts.

    Detection strategy
    ------------------
    • Use ``git grep -l "<<<<<<<"`` — Git writes this exact marker at the start
      of the “ours” hunk whenever it cannot auto-merge.
    • Exit-status semantics:

        0 → at least one match (conflict present)  
        1 → no match (clean)  
        ≥2 → actual error → raise ``GitError``

    Raises
    ------
    GitError
        If *git grep* fails for reasons other than “no match”.
    """
    result = subprocess.run(                            # noqa: S603,S607
        ["git", "grep", "-l", "<<<<<<<", "--", "."],
        cwd=path,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True          # conflict markers found
    if result.returncode == 1:
        return False         # no markers
    # Anything else is a genuine error
    raise GitError(result.stderr.strip() or "git grep failed")


# Helper: last-N commits
def get_last_commits(
    path: Path | str = ".", n: int = 10
) -> list[dict[str, str]]:  # pragma: no cover
    """
    Return metadata for the last *n* commits on the current branch.

    Each dict contains:
        { "hash": <full>, "abbrev": <short>, "author": <name>,
          "date": <YYYY-MM-DD>, "subject": <message> }
    """
    fmt = "%H%x1f%h%x1f%an%x1f%ad%x1f%s"
    raw = _run_git(
        ["log", f"-n{n}", "--date=short", f"--pretty={fmt}"], cwd=path
    )
    commits: list[dict[str, str]] = []
    for line in raw.splitlines():
        full, short, author, date, subject = line.split("\x1f")
        commits.append(
            {
                "hash": full,
                "abbrev": short,
                "author": author,
                "date": date,
                "subject": subject.strip(),
            }
        )
    return commits
