"""
Tests for b3th.summarizer.summarize_commits()

We stub:
  • is_git_repo           → True
  • get_last_commits      → deterministic list
  • llm.chat_completion   → fixed summary
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from b3th import summarizer as sm

FAKE_COMMITS = [
    {
        "hash": "a" * 40,
        "abbrev": "a1b2c3d",
        "author": "Alice",
        "date": "2025-06-15",
        "subject": "feat(core): add stats command",
    },
    {
        "hash": "b" * 40,
        "abbrev": "b7c8d9e",
        "author": "Bob",
        "date": "2025-06-14",
        "subject": "fix(ui): correct button color",
    },
]


def test_summarizer_happy_path(monkeypatch, tmp_path: Path):
    """Returns the LLM summary string."""

    # Make repo_path look like a Git repo
    monkeypatch.setattr(sm, "is_git_repo", lambda _: True, raising=True)
    # Stub commit extraction
    monkeypatch.setattr(sm, "get_last_commits", lambda *_: FAKE_COMMITS, raising=True)

    fake_summary = (
        "Add a comprehensive stats command and fix a minor UI color issue, "
        "enhancing both functionality and visual consistency."
    )
    with patch.object(sm.llm, "chat_completion", return_value=fake_summary):
        out = sm.summarize_commits(tmp_path, n=2)

    assert out.startswith("Add a comprehensive stats command")
    assert "UI color issue" in out


def test_summarizer_llm_failure(monkeypatch, tmp_path: Path):
    """LLM exceptions should be surfaced as SummarizerError."""

    monkeypatch.setattr(sm, "is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr(sm, "get_last_commits", lambda *_: FAKE_COMMITS, raising=True)

    # Simulate Groq API error
    with patch.object(sm.llm, "chat_completion", side_effect=sm.llm.LLMError("boom")):
        with pytest.raises(sm.SummarizerError):
            sm.summarize_commits(tmp_path, n=2)
