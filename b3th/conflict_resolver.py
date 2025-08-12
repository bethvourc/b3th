"""
Analyse unresolved Git merge conflicts *and* let Groq propose resolutions.

Public API
----------
list_conflicted_files(repo)        -> list[Path]
extract_conflict_hunks(path)       -> list[dict]
build_resolution_prompt(repo)      -> str | None
resolve_conflicts(repo, model=…)   -> list[Path] 
"""

from __future__ import annotations

import re
from pathlib import Path

from .git_utils import _run_git  # low-level helper
from .llm import chat_completion  # Groq wrapper

# 1. Locate conflicted files
_CONFLICT_MARKER = "<<<<<<< "  # Git always adds a space after <<<<<<<


def list_conflicted_files(repo: str | Path = ".") -> list[Path]:
    """Return a list of *tracked* files that still have conflict markers."""
    try:
        raw = _run_git(["grep", "-l", _CONFLICT_MARKER, "--", "."], cwd=repo)
        return [Path(repo, p) for p in raw.splitlines()] if raw else []
    except Exception:  # noqa: BLE001 – GitError / not-repo
        return []


# 2. Parse hunks from a given file
_HUNK_RE = re.compile(
    r"""
    ^<<<<<<<[ ]+(?P<ours>.*?)\n
    (?P<left>.*?)
    ^=======$\n
    (?P<right>.*?)
    ^>>>>>>>[ ]+(?P<theirs>.*?)$
    """,
    re.M | re.S | re.X,
)


def extract_conflict_hunks(path: str | Path) -> list[dict[str, str]]:
    """Return list of dicts {ours_label, theirs_label, left, right} per hunk."""
    hunks: list[dict[str, str]] = []
    for m in _HUNK_RE.finditer(Path(path).read_text()):
        hunks.append(
            {
                "ours_label": m["ours"].strip(),
                "theirs_label": m["theirs"].strip(),
                "left": m["left"].rstrip("\n"),
                "right": m["right"].rstrip("\n"),
            }
        )
    return hunks


# 3. Build prompt (multi-file)
_PROMPT_HEADER = (
    "You are an expert Git merge-conflict resolver. For every conflict below, "
    "return the **merged file content only**, no commentary.\n"
)


def _format_hunk(i: int, h: dict[str, str]) -> str:
    return (
        f"### Conflict {i}\n"
        "```diff\n"
        "<<<<<<< ours\n"
        f"{h['left']}\n"
        "=======\n"
        f"{h['right']}\n"
        ">>>>>>> theirs\n"
        "```"
    )


def build_resolution_prompt(repo: str | Path = ".") -> str | None:
    """Combine all conflicted files into one markdown prompt for Groq."""
    files = list_conflicted_files(repo)
    if not files:
        return None

    parts: list[str] = [_PROMPT_HEADER]
    for f in files:
        hunks = extract_conflict_hunks(f)
        if not hunks:
            continue
        parts.append(f"\n## File: `{Path(f).name}`")
        for i, h in enumerate(hunks, 1):
            parts.append(_format_hunk(i, h))
    return "\n\n".join(parts).strip()


# 4. NEW – Ask Groq & write <file>.resolved
def resolve_conflicts(
    repo: str | Path = ".",
    *,
    model: str | None = None,
) -> list[Path]:
    """
    For every conflicted file in *repo* call the LLM and write `<file>.resolved`.

    Returns the list of generated `.resolved` paths.
    """
    resolved_paths: list[Path] = []
    for f in list_conflicted_files(repo):
        hunks = extract_conflict_hunks(f)
        if not hunks:
            continue

        # Build per-file prompt (smaller ⇒ cheaper tokens)
        prompt_lines = [_PROMPT_HEADER, f"## File: `{Path(f).name}`"]
        for i, h in enumerate(hunks, 1):
            prompt_lines.append(_format_hunk(i, h))
        prompt = "\n\n".join(prompt_lines)

        merged_text: str = chat_completion(prompt, model=model)  # type: ignore[arg-type]
        out_path = f.with_suffix(f.suffix + ".resolved")
        Path(out_path).write_text(merged_text.rstrip() + "\n")
        resolved_paths.append(out_path)

    return resolved_paths
