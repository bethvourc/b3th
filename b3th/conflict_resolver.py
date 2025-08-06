"""
Utilities for analysing unresolved Git merge conflicts and preparing
an LLM-friendly resolution prompt.

Public API
----------
list_conflicted_files(repo) -> list[Path]
extract_conflict_hunks(path) -> list[dict]
build_resolution_prompt(repo) -> str
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict, Optional, Union

from .git_utils import _run_git  # re-use low-level helper from step 4


# Locate files that still contain "<<<<<<<" markers
_CONFLICT_MARKER = "<<<<<<< "  # Git always adds a space after the marker


def list_conflicted_files(repo: Union[str, Path] = ".") -> List[Path]:
    """
    Return a list of files that contain unresolved merge markers.

    Uses ``git grep -l "<<<<<<< "`` for speed; falls back to an empty list
    if repo is not a Git repository.
    """
    try:
        raw = _run_git(["grep", "-l", _CONFLICT_MARKER, "--", "."], cwd=repo)
        if not raw:
            return []
        return [Path(repo, line.strip()) for line in raw.splitlines()]
    except Exception:  # noqa: BLE001  (GitError or not-a-git-repo)
        return []



# Parse conflict hunks from a single file
_HUNK_RE = re.compile(
    r"""
    ^<<<<<<<[ ]+(?P<ours>.*?)\n          # ours marker
    (?P<left>.*?)
    ^=======$\n                          # split
    (?P<right>.*?)
    ^>>>>>>>[ ]+(?P<theirs>.*?)$         # theirs marker
""",
    re.M | re.S | re.X,
)


def extract_conflict_hunks(path: Union[str, Path]) -> List[Dict[str, str]]:
    """
    Return a list of dicts, one per conflict hunk in *path*.

    Dict keys: ``ours_label``, ``theirs_label``, ``left``, ``right``.
    """
    text = Path(path).read_text()
    hunks: List[Dict[str, str]] = []
    for match in _HUNK_RE.finditer(text):
        hunks.append(
            {
                "ours_label": match["ours"].strip(),
                "theirs_label": match["theirs"].strip(),
                "left": match["left"].rstrip("\n"),
                "right": match["right"].rstrip("\n"),
            }
        )
    return hunks



# Build Groq prompt
def _format_hunk(i: int, h: Dict[str, str]) -> str:
    return (
        f"### Conflict {i}\n"
        f"*Ours*: `{h['ours_label']}` — *Theirs*: `{h['theirs_label']}`\n"
        "```diff\n"
        "<<<<<<< ours\n"
        f"{h['left']}\n"
        "=======\n"
        f"{h['right']}\n"
        ">>>>>>> theirs\n"
        "```"
    )


_PROMPT_HEADER = """\
You are an expert Git merge-conflict resolver. For each conflict below,
produce the best merged version **only as final code**, no explanations.
"""


def build_resolution_prompt(repo: Union[str, Path] = ".") -> Optional[str]:
    """
    Return a single Markdown prompt for Groq, or *None* if no conflicts.
    """
    files = list_conflicted_files(repo)
    if not files:
        return None

    parts: List[str] = [_PROMPT_HEADER]
    for f in files:
        hunks = extract_conflict_hunks(f)
        if not hunks:
            continue
        parts.append(f"\n## File: `{f}`")
        for i, hunk in enumerate(hunks, 1):
            parts.append(_format_hunk(i, hunk))

    return "\n\n".join(parts).strip()
