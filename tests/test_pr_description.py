"""
Unit tests for generate_pr_description().

All git and network interactions are stubbed.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from b3th import pr_description as prd

FAKE_DIFF = """
 foo.py | 2 +-
 bar.py | 1 +
 2 files changed, 2 insertions(+), 1 deletion(-)
"""

FAKE_COMMITS = """
feat: add new api
fix: handle edge case
docs: update readme
"""


def test_pr_description_success(monkeypatch, tmp_path: Path):
    """Happy path returns title/body parsed from LLM reply."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(prd, "is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr(prd, "_branch_diff", lambda *_: FAKE_DIFF, raising=True)
    monkeypatch.setattr(prd, "_commit_messages", lambda *_: FAKE_COMMITS, raising=True)

    fake_reply = (
        "add comprehensive api and docs\n\n"
        "* Introduces the new endpoint with full validation.\n"
        "* Fixes an edge case in error handling.\n"
        "* Updates README to reflect API changes."
    )

    with patch.object(prd.llm, "chat_completion", return_value=fake_reply):
        title, body = prd.generate_pr_description(repo)

    assert title.startswith("add comprehensive api")
    assert "* Introduces the new endpoint" in body


def test_pr_description_no_changes(monkeypatch, tmp_path: Path):
    """Empty diff should raise PRDescriptionError."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(prd, "is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr(prd, "_branch_diff", lambda *_: "", raising=True)

    with pytest.raises(prd.PRDescriptionError):
        prd.generate_pr_description(repo)
