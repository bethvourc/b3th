# tests/test_gh_api.py
"""
Unit tests for gh_api PR creation and helpers.

All git/network interactions are stubbed so no external calls happen.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import pytest
import requests

from b3th import gh_api


# ----------------------- Happy paths -----------------------


def test_create_pr_happy_path(monkeypatch, tmp_path: Path):
    """Successful PR creation returns the HTML URL (token path)."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Pretend we are inside a git repo
    monkeypatch.setattr(gh_api, "is_git_repo", lambda _: True, raising=True)

    # Stub token
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok", raising=True)

    # Stub branch + remote helpers
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda *_: "me/project", raising=True)
    monkeypatch.setattr(
        gh_api, "_push_current_branch", lambda *_: "feature-branch", raising=True
    )

    # Fake GitHub response
    fake_resp = SimpleNamespace(
        status_code=201,
        json=lambda: {"html_url": "https://github.com/me/project/pull/1"},
        text='{"html_url":"https://github.com/me/project/pull/1"}',
    )

    with patch("requests.post", return_value=fake_resp) as mock_post:
        pr_url = gh_api.create_pull_request(
            "Add feature", "Detailed PR body", repo_path=repo
        )

    assert pr_url == "https://github.com/me/project/pull/1"
    # Verify HTTP call
    mock_post.assert_called_once()
    url = mock_post.call_args.args[0]
    assert url.endswith("/repos/me/project/pulls")


def test_create_draft_pr(monkeypatch, tmp_path: Path):
    """Draft PR should include 'draft': true in payload."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Stubs
    monkeypatch.setattr(gh_api, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok", raising=True)
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda *_: "me/project", raising=True)
    monkeypatch.setattr(gh_api, "_push_current_branch", lambda *_: "feat-x", raising=True)

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=30):  # noqa: ANN001
        captured["payload"] = json
        return SimpleNamespace(
            status_code=201,
            json=lambda: {"html_url": "https://github.com/me/project/pull/99"},
            text='{"html_url":"https://github.com/me/project/pull/99"}',
        )

    # Patch the module-local requests instance
    monkeypatch.setattr("b3th.gh_api.requests.post", fake_post, raising=True)

    pr_url = gh_api.create_draft_pull_request("WIP: feat", "body", repo_path=repo)
    assert pr_url.endswith("/pull/99")
    assert captured["payload"]["draft"] is True


# ----------------------- Error paths (token) -----------------------


def test_create_pr_github_error(monkeypatch, tmp_path: Path):
    """Non-2xx GitHub response should raise GitHubAPIError."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(gh_api, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok", raising=True)
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda *_: "me/project", raising=True)
    monkeypatch.setattr(gh_api, "_push_current_branch", lambda *_: "feature-branch", raising=True)

    bad_resp = SimpleNamespace(status_code=422, text="boom", json=lambda: {})
    with patch("requests.post", return_value=bad_resp):
        with pytest.raises(gh_api.GitHubAPIError):
            gh_api.create_pull_request("x", "y", repo_path=repo)


def test_create_pr_201_missing_html_url(monkeypatch, tmp_path: Path):
    """201 but body has no html_url → GitHubAPIError."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(gh_api, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok", raising=True)
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda *_: "me/project", raising=True)
    monkeypatch.setattr(gh_api, "_push_current_branch", lambda *_: "feature-branch", raising=True)

    ok_resp_no_url = SimpleNamespace(status_code=201, json=lambda: {"id": 1}, text='{"id":1}')
    with patch("requests.post", return_value=ok_resp_no_url):
        with pytest.raises(gh_api.GitHubAPIError):
            gh_api.create_pull_request("title", "body", repo_path=repo)


def test_create_pr_json_raises(monkeypatch, tmp_path: Path):
    """requests.post succeeds but .json() throws → GitHubAPIError."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(gh_api, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok", raising=True)
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda *_: "me/project", raising=True)
    monkeypatch.setattr(gh_api, "_push_current_branch", lambda *_: "feature-branch", raising=True)

    class BadJSONResp:
        status_code = 201
        text = "ok"

        def json(self):
            raise ValueError("bad json")

    with patch("requests.post", return_value=BadJSONResp()):
        with pytest.raises(gh_api.GitHubAPIError):
            gh_api.create_pull_request("t", "b", repo_path=repo)


def test_create_pr_network_error_raises(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(gh_api, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok", raising=True)
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda *_: "me/project", raising=True)
    monkeypatch.setattr(gh_api, "_push_current_branch", lambda *_: "feat-y", raising=True)

    def boom(*_a, **_k):
        raise requests.RequestException("down")

    monkeypatch.setattr(gh_api.requests, "post", boom, raising=True)

    with pytest.raises(gh_api.GitHubAPIError):
        gh_api.create_pull_request("title", "body", repo_path=repo)


# ----------------------- gh CLI fallback (no token) -----------------------


def test_create_pr_uses_gh_cli_when_no_token(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    # Pretend it's a git repo and avoid any real git calls.
    monkeypatch.setattr(gh_api, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda *_: "me/project", raising=True)
    monkeypatch.setattr(gh_api, "_push_current_branch", lambda *_: "feat-x", raising=True)

    # Force the no-token path so _post_json uses `gh api`.
    def raise_cfg():
        raise gh_api.ConfigError("missing")

    monkeypatch.setattr(gh_api, "get_github_token", raise_cfg, raising=True)

    captured = {}

    def fake_run(cmd, input=None, text=False, capture_output=False):  # noqa: ANN001
        captured["cmd"] = cmd
        captured["input"] = input
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"html_url": "https://github.com/me/project/pull/123"}),
            stderr="",
        )

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run, raising=True)

    url = gh_api.create_pull_request("t", "b", repo_path=repo)
    assert url.endswith("/pull/123")
    assert any(s.endswith("/repos/me/project/pulls") for s in captured["cmd"])

    body = json.loads(captured["input"])
    assert body["title"] == "t"
    assert body["body"] == "b"


def test_post_json_parses_malformed_gh_output(monkeypatch):
    """gh CLI returns non-JSON → GitHubAPIError."""
    # Force the no-token path
    def raise_cfg():
        raise gh_api.ConfigError("missing")

    monkeypatch.setattr(gh_api, "get_github_token", raise_cfg, raising=True)

    # Simulate `gh api` returning invalid JSON
    def fake_run(cmd, input=None, text=False, capture_output=False):  # noqa: ANN001
        return SimpleNamespace(returncode=0, stdout="not-json", stderr="")

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run, raising=True)

    with pytest.raises(gh_api.GitHubAPIError):
        gh_api._post_json("/repos/x/y/pulls", {"x": 1})


def test_gh_cli_nonzero_exit(monkeypatch, tmp_path: Path):
    """gh CLI returns non-zero → GitHubAPIError."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(gh_api, "is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda *_: "me/project", raising=True)
    monkeypatch.setattr(gh_api, "_push_current_branch", lambda *_: "feat-x", raising=True)

    # No token → gh path
    def raise_cfg():
        raise gh_api.ConfigError("missing")

    monkeypatch.setattr(gh_api, "get_github_token", raise_cfg, raising=True)

    # gh api fails
    def fake_run(cmd, input=None, text=False, capture_output=False):  # noqa: ANN001
        return SimpleNamespace(returncode=1, stdout="", stderr="fail!")

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run, raising=True)

    with pytest.raises(gh_api.GitHubAPIError):
        gh_api.create_pull_request("t", "b", repo_path=repo)


# ----------------------- Helper coverage -----------------------


@pytest.mark.parametrize(
    "remote, expected",
    [
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo", "owner/repo"),
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo", "owner/repo"),
    ],
)
def test_slug_from_remote_variants(remote, expected):
    assert gh_api._slug_from_remote(remote) == expected


def test_slug_from_remote_invalid():
    with pytest.raises(gh_api.GitRepoError):
        gh_api._slug_from_remote("file:///tmp/repo")  # not a supported GitHub URL


def test_post_json_token_uses_requests_headers(monkeypatch):
    """With a token, _post_json should use requests and set headers."""
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok-123", raising=True)

    captured = {}

    class FakeResp:
        status_code = 201

        def json(self):
            return {"ok": 1}

        text = '{"ok":1}'

    def fake_post(url, headers=None, json=None, timeout=30):  # noqa: ANN001
        captured["url"] = url
        captured["headers"] = headers or {}
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(gh_api.requests, "post", fake_post, raising=True)

    out = gh_api._post_json("/repos/me/project/pulls", {"a": 1})
    assert out["ok"] == 1
    assert captured["url"].endswith("/repos/me/project/pulls")
    auth = captured["headers"].get("Authorization", "")
    # Support either common scheme the code may use
    assert auth.startswith("Bearer ") or auth.startswith("token ")
    accept = captured["headers"].get("Accept", "")
    assert accept.startswith("application/vnd.github+json")
    assert captured["json"] == {"a": 1}
    assert captured["timeout"] == 30


def test_run_git_raises_on_nonzero(monkeypatch):
    """_run_git should raise GitRepoError when git exits non-zero."""
    def fake_run(*_a, **_k):
        return SimpleNamespace(returncode=1, stdout="", stderr="fatal: bad")

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run, raising=True)

    with pytest.raises(gh_api.GitRepoError):
        gh_api._run_git(["status"])


def test_get_repo_slug_uses_run_git(monkeypatch, tmp_path: Path):
    """_get_repo_slug should parse origin remote via _run_git + _slug_from_remote."""
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setattr(gh_api, "is_git_repo", lambda p: True, raising=True)

    def fake_run_git(args, cwd=None):  # noqa: ANN001
        # Expect a call like: git config --get remote.origin.url
        assert "config" in args and "remote.origin.url" in args
        return "https://github.com/owner/repo.git\n"

    # Normalize inside the helper
    monkeypatch.setattr(gh_api, "_run_git", fake_run_git, raising=True)
    monkeypatch.setattr(gh_api, "_slug_from_remote", lambda s: "owner/repo", raising=True)

    slug = gh_api._get_repo_slug(repo)
    assert slug == "owner/repo"


def test_push_current_branch_success(monkeypatch, tmp_path: Path):
    """_push_current_branch returns current branch name and 'pushes' it."""
    repo = tmp_path / "repo"
    repo.mkdir()

    calls = {"push": 0}

    # Patch where it's used (inside gh_api), so we don't hit real git
    monkeypatch.setattr("b3th.gh_api.get_current_branch", lambda p: "feat-branch", raising=True)

    def fake_run_git(args, cwd=None):  # noqa: ANN001
        # Expect a push command
        assert "push" in args
        calls["push"] += 1
        return ""

    monkeypatch.setattr(gh_api, "_run_git", fake_run_git, raising=True)

    branch = gh_api._push_current_branch(repo)
    assert branch == "feat-branch"
    assert calls["push"] == 1


def test_push_current_branch_failure(monkeypatch, tmp_path: Path):
    """_push_current_branch propagates GitRepoError from _run_git (push step)."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Patch where it's used (inside gh_api)
    monkeypatch.setattr("b3th.gh_api.get_current_branch", lambda p: "feat-branch", raising=True)

    def boom(*_a, **_k):
        raise gh_api.GitRepoError("fail")

    monkeypatch.setattr(gh_api, "_run_git", boom, raising=True)

    with pytest.raises(gh_api.GitRepoError):
        gh_api._push_current_branch(repo)
