"""
Generate an AI-powered commit message from staged changes.

Usage:
    subject, body = generate_commit_message(repo_path=".")
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from . import git_utils, llm


class CommitMessageError(RuntimeError):
    """Raised when a commit message cannot be generated."""


# Prompt building helpers
_SYSTEM_PROMPT: str = (
    "You are an expert Git assistant. "
    "Given a unified diff, create a high-quality commit message in this exact format:\n"
    "1. A concise subject line (≤ 72 chars, lowercase imperative mood, includes scope if obvious)\n"
    "2. A blank line\n"
    "3. A detailed body wrapped at 72 chars per line explaining the WHY, not the HOW.\n"
    "Do not include code fences, backticks, or any additional sections."
)


def _build_messages(diff: str) -> list[dict[str, str]]:
    """Return the message list expected by llm.chat_completion()."""
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": textwrap.dedent(
                f"""
                Here is the staged diff:

                ```
                {diff}
                ```

                Generate the commit message now.
                """
            ).strip(),
        },
    ]


# Public API
def generate_commit_message(
    repo_path: str | Path = ".",
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 300,
) -> tuple[str, str]:
    """
    Return (subject, body) strings for the current staged diff.

    Raises
    ------
    CommitMessageError
        If no staged changes are found or the LLM call fails.
    """
    diff = git_utils.get_staged_diff(repo_path)
    if not diff.strip():
        raise CommitMessageError("No staged changes detected.")

    try:
        response = llm.chat_completion(
            _build_messages(diff),
            model=model,  # None → llm._default_model()
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except llm.LLMError as exc:
        raise CommitMessageError(str(exc)) from exc

    # Parse: first non-empty line = subject, rest (after first blank) = body
    lines = [ln.rstrip() for ln in response.splitlines()]
    # drop leading/trailing blank lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    if not lines:
        raise CommitMessageError("LLM returned an empty response.")

    subject = lines[0]
    # body starts after the first blank line *or* immediately after subject
    try:
        blank_idx = lines.index("", 1)
        body_lines = lines[blank_idx + 1 :]
    except ValueError:
        body_lines = lines[1:]

    body = "\n".join(body_lines).strip()
    return subject.strip(), body
