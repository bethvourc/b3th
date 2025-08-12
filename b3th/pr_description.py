"""
Generate an AI-crafted pull-request title and body.

Usage:
    title, body = generate_pr_description(repo_path=".", base="main")
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from . import llm
from .git_utils import GitError, is_git_repo


class PRDescriptionError(RuntimeError):
    """Raised when a pull-request description cannot be generated."""


# Internal git helpers
def _run_git(args: list[str], cwd: Path | str | None = None) -> str:
    """Run `git <args>` and return stdout (strip newline)."""
    result = subprocess.run(  # noqa: S603,S607
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _branch_diff(repo_path: str | Path, base: str) -> str:
    """Return `git diff --stat` output between *base* and HEAD."""
    return _run_git(["diff", "--stat", f"{base}..HEAD"], cwd=repo_path)


def _commit_messages(repo_path: str | Path, base: str) -> str:
    """Return one-line commit summaries between *base* and HEAD (oldest→newest)."""
    return _run_git(["log", "--reverse", "--pretty=%s", f"{base}..HEAD"], cwd=repo_path)


# Prompt helpers
_SYSTEM_PROMPT: str = (
    "You are an expert GitHub assistant. "
    "Given a branch diff summary and the commit subjects, craft a high-quality "
    "pull-request with:\n"
    "• A concise, descriptive title (≤ 72 chars, lowercase imperative mood)\n"
    "• A blank line\n"
    "• A detailed body in markdown explaining WHY the changes are needed, "
    "what they do, and any breaking changes or follow-up tasks. "
    "Wrap text at 72 chars per line.\n"
    "Do not include code fences or extra sections."
)


def _build_messages(diff: str, commits: str) -> list[dict[str, str]]:
    """Return the list of messages for llm.chat_completion()."""
    user_msg = textwrap.dedent(
        f"""
        Here is the diff summary between the base branch and HEAD:

        ```
        {diff}
        ```

        And here are the commit subjects (oldest first):

        ```
        {commits}
        ```

        Generate the pull-request title and body now.
        """
    ).strip()

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


# Public API
def generate_pr_description(
    repo_path: str | Path = ".",
    *,
    base: str = "main",
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
) -> tuple[str, str]:
    """
    Return (title, body) strings for a pull-request.

    Raises
    ------
    PRDescriptionError
        When the diff is empty or the LLM fails.
    """
    repo_path = Path(repo_path)

    if not is_git_repo(repo_path):
        raise PRDescriptionError(f"{repo_path} is not a Git repository.")

    diff = _branch_diff(repo_path, base)
    if not diff.strip():
        raise PRDescriptionError("No changes between HEAD and base branch.")

    commits = _commit_messages(repo_path, base)

    try:
        response = llm.chat_completion(
            _build_messages(diff, commits),
            model=model,  # None → default model
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except llm.LLMError as exc:
        raise PRDescriptionError(str(exc)) from exc

    # Parse: first non-empty line → title; rest (after first blank) → body
    lines = [ln.rstrip() for ln in response.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    if not lines:
        raise PRDescriptionError("LLM returned an empty response.")

    title = lines[0]
    try:
        blank_idx = lines.index("", 1)
        body_lines = lines[blank_idx + 1 :]
    except ValueError:
        body_lines = lines[1:]

    body = "\n".join(body_lines).strip()
    return title.strip(), body
