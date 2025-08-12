"""
stats.py – Git statistics for a given time-frame.

Example:
    stats = get_stats(".", last="7d")
    # -> {"commits": 14, "files": 6, "additions": 120, "deletions": 34}
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from .git_utils import is_git_repo, run_git


class StatsError(RuntimeError):
    """Raised when statistics cannot be collected."""


# Helpers
def _parse_last(value: str | None) -> str | None:
    """Convert '7d', '2w', '1m' to ISO date for `git --since`."""
    if value is None:
        return None

    m = re.fullmatch(r"(\d+)([dwm])", value.strip())
    if not m:
        raise StatsError("Invalid --last value (use Nd, Nw, or Nm)")

    amount, unit = int(m.group(1)), m.group(2)
    delta = (
        timedelta(days=amount)
        if unit == "d"
        else timedelta(weeks=amount) if unit == "w" else timedelta(days=30 * amount)
    )
    return (datetime.now() - delta).strftime("%Y-%m-%d")


# Core API
def get_stats(
    repo_path: str | Path = ".", *, last: str | None = None
) -> dict[str, int]:
    """Return commit count, unique files changed, insertions, deletions."""
    repo_path = Path(repo_path)
    if not is_git_repo(repo_path):
        raise StatsError(f"{repo_path} is not a Git repository")

    since_arg = _parse_last(last)
    log_range = ["--since", since_arg] if since_arg else []

    # commits
    log_output = run_git(
        ["log", "--all", "--oneline", *log_range, "--pretty=%h"], cwd=repo_path
    )
    commit_count = len(log_output.splitlines()) if log_output else 0

    if commit_count == 0:
        return {"commits": 0, "files": 0, "additions": 0, "deletions": 0}

    # numstat for file/line counts
    numstat = run_git(
        ["log", "--all", *log_range, "--pretty=tformat:", "--numstat"],
        cwd=repo_path,
    )

    files = set()
    additions = deletions = 0
    for line in numstat.splitlines():
        add, delete, filename = line.split("\t")
        numeric_add = add.isdigit()
        numeric_del = delete.isdigit()

        if numeric_add:
            additions += int(add)
        if numeric_del:
            deletions += int(delete)

        # Only count text files (numeric stats) toward unique file total
        if numeric_add or numeric_del:
            files.add(filename)

    return {
        "commits": commit_count,
        "files": len(files),
        "additions": additions,
        "deletions": deletions,
    }


# CLI helper
def print_stats(
    repo_path: str | Path = ".", last: str | None = None
) -> None:  # pragma: no cover
    """Pretty-print stats to stdout (used by `b3th stats`)."""
    data = get_stats(repo_path, last=last)
    if data["commits"] == 0:
        print("No commits in the specified range.")
        return

    print(
        f"Commits:    {data['commits']}\n"
        f"Files:      {data['files']}\n"
        f"Additions:  +{data['additions']}\n"
        f"Deletions:  -{data['deletions']}"
    )
