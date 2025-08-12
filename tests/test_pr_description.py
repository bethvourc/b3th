"""
Unit tests for generate_pr_description().

All git and network interactions are stubbed.
"""

from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

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


def test_pr_description_llm_error(monkeypatch, tmp_path: Path):
    """If the LLM call fails, the function should raise PRDescriptionError."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(prd, "is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr(prd, "_branch_diff", lambda *_: FAKE_DIFF, raising=True)
    monkeypatch.setattr(prd, "_commit_messages", lambda *_: FAKE_COMMITS, raising=True)

    LLMError = getattr(prd.llm, "LLMError", RuntimeError)
    with patch.object(prd.llm, "chat_completion", side_effect=LLMError("down")):
        with pytest.raises(prd.PRDescriptionError):
            prd.generate_pr_description(repo)


def test_pr_description_title_only(monkeypatch, tmp_path: Path):
    """If LLM returns only a title line, body should be empty after trimming."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(prd, "is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr(prd, "_branch_diff", lambda *_: FAKE_DIFF, raising=True)
    monkeypatch.setattr(prd, "_commit_messages", lambda *_: FAKE_COMMITS, raising=True)

    # Leading/trailing blank lines & spaces; no body content.
    reply = "\nAdd feature XYZ  \n\n"
    with patch.object(prd.llm, "chat_completion", return_value=reply):
        title, body = prd.generate_pr_description(repo)

    assert title == "Add feature XYZ"
    assert body == ""


def test_pr_description_not_git_repo(monkeypatch, tmp_path: Path):
    """Early guard: non-repo path should raise PRDescriptionError."""
    repo = tmp_path / "repo"; repo.mkdir()
    monkeypatch.setattr(prd, "is_git_repo", lambda *_: False, raising=True)

    with pytest.raises(prd.PRDescriptionError) as ex:
        prd.generate_pr_description(repo)
    assert "is not a Git repository" in str(ex.value)


def test_pr_description_git_diff_error(monkeypatch, tmp_path: Path):
    """
    _run_git error path: git diff returns non-zero -> GitError.
    We patch subprocess.run used by _run_git().
    """
    repo = tmp_path / "repo"; repo.mkdir()
    monkeypatch.setattr(prd, "is_git_repo", lambda *_: True, raising=True)

    def fake_run(*_a, **_k):
        # Simulate 'git diff --stat' failing
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(prd.subprocess, "run", fake_run, raising=True)

    with pytest.raises(prd.GitError) as ex:
        prd.generate_pr_description(repo)
    assert "boom" in str(ex.value)


def test_build_messages_shape_and_content():
    """_build_messages should include system prompt and embed diff/commits."""
    diff = "file.py | 3 ++-\n 1 file changed, 2 insertions(+), 1 deletion(-)"
    commits = "feat: add X\nfix: Y"
    msgs = prd._build_messages(diff, commits)
    assert isinstance(msgs, list) and len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert "expert GitHub assistant" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    user = msgs[1]["content"]
    assert "diff summary" in user or "diff" in user.lower()  # wording safety
    assert diff in user
    assert commits in user


def test_pr_description_empty_llm_response(monkeypatch, tmp_path: Path):
    """Empty/whitespace-only LLM output → PRDescriptionError."""
    repo = tmp_path / "repo"; repo.mkdir()

    monkeypatch.setattr(prd, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(prd, "_branch_diff", lambda *_: "a.diff", raising=True)
    monkeypatch.setattr(prd, "_commit_messages", lambda *_: "c", raising=True)

    with patch.object(prd.llm, "chat_completion", return_value=" \n  \n"):
        with pytest.raises(prd.PRDescriptionError) as ex:
            prd.generate_pr_description(repo)
    assert "empty response" in str(ex.value).lower()


def test_pr_description_passes_params_to_llm(monkeypatch, tmp_path: Path):
    """Ensure model/temperature/max_tokens are forwarded to llm.chat_completion()."""
    repo = tmp_path / "repo"; repo.mkdir()

    monkeypatch.setattr(prd, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(prd, "_branch_diff", lambda *_: "D", raising=True)
    monkeypatch.setattr(prd, "_commit_messages", lambda *_: "C", raising=True)

    called = {}
    def fake_chat_completion(messages, *, model, temperature, max_tokens):
        called["model"] = model
        called["temperature"] = temperature
        called["max_tokens"] = max_tokens
        # minimal well-formed response
        return "title line\n\nbody line 1\nbody line 2"

    with patch.object(prd.llm, "chat_completion", side_effect=fake_chat_completion):
        title, body = prd.generate_pr_description(
            repo, model="gptx", temperature=0.3, max_tokens=123
        )

    assert title == "title line"
    assert "body line 1" in body
    assert called == {"model": "gptx", "temperature": 0.3, "max_tokens": 123}


def test_pr_description_base_param_propagates(monkeypatch, tmp_path: Path):
    """Custom base branch should be passed through to git helpers."""
    repo = tmp_path / "repo"; repo.mkdir()
    monkeypatch.setattr(prd, "is_git_repo", lambda *_: True, raising=True)

    seen = {"diff_base": None, "log_base": None}

    def fake_diff(path, base):
        seen["diff_base"] = base
        return "x | 1 +"

    def fake_commits(path, base):
        seen["log_base"] = base
        return "feat: x"

    monkeypatch.setattr(prd, "_branch_diff", fake_diff, raising=True)
    monkeypatch.setattr(prd, "_commit_messages", fake_commits, raising=True)

    with patch.object(prd.llm, "chat_completion", return_value="t\n\nb"):
        title, body = prd.generate_pr_description(repo, base="develop")

    assert title == "t" and body == "b"
    assert seen["diff_base"] == "develop"
    assert seen["log_base"] == "develop"


def test__run_git_success_strips_newlines(monkeypatch, tmp_path: Path):
    """Directly cover the happy path in _run_git()."""
    def fake_run(*_a, **_k):
        return SimpleNamespace(returncode=0, stdout=" ok\n", stderr="")
    monkeypatch.setattr(prd.subprocess, "run", fake_run, raising=True)
    out = prd._run_git(["status"])
    assert out == "ok"