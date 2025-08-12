"""
summarizer.py – commit summarization utilities.

Step 6: send commit list to Groq and return a natural-language paragraph.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from . import llm
from .git_utils import get_last_commits, is_git_repo


class SummarizerError(RuntimeError):
    """Raised when commits cannot be summarized."""


# Data extraction helpers
def _commits_markdown(commits: list[dict]) -> str:
    """Convert commit dicts to a clean Markdown bullet list."""
    return "\n".join(f"* {c['date']}  {c['abbrev']}  {c['subject']}" for c in commits)


def prepare_commits_for_llm(repo_path: str | Path = ".", n: int = 10) -> str:
    """
    Return a Markdown bullet list of the last *n* commits.

    Raises
    ------
    SummarizerError
    """
    repo_path = Path(repo_path)
    if not is_git_repo(repo_path):
        raise SummarizerError(f"{repo_path} is not a Git repository")

    commits = get_last_commits(repo_path, n)
    if not commits:
        raise SummarizerError("No commits found.")

    return _commits_markdown(commits)


# Public API
_SYSTEM_PROMPT = (
    "You are a helpful assistant who summarises Git commit history. "
    "Given a bullet list of commits (newest last), produce ONE paragraph "
    "that captures the overall changes, themes, and impact. Aim for ~80-120 "
    "words, use present-tense imperative mood (e.g., 'Add X', 'Fix Y'), "
    "and avoid low-level file names."
)


def summarize_commits(
    repo_path: str | Path = ".", n: int = 10, *, model: str | None = None
) -> str:
    """
    Return an LLM-generated paragraph summarising the last *n* commits.
    """
    bullet_list = prepare_commits_for_llm(repo_path, n)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": textwrap.dedent(
                f"""
                Here are the last {n} commits:

                {bullet_list}

                Summarise them in one paragraph now.
                """
            ).strip(),
        },
    ]
    try:
        summary = llm.chat_completion(messages, model=model or None, max_tokens=150)
    except llm.LLMError as exc:
        raise SummarizerError(str(exc)) from exc

    return summary.strip()
