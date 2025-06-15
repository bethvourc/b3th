"""
Unit tests for gh_api.create_pull_request.

We stub out every network and git interaction so no external calls happen.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from b3th import gh_api


def test_create_pr_happy_path(monkeypatch, tmp_path: Path):
    """Successful PR creation returns the HTML URL."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Pretend we are inside a git repo
    monkeypatch.setattr(gh_api, "is_git_repo", lambda _: True, raising=True)

    # Stub token
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok", raising=True)

    # Stub branch + remote helpers
    monkeypatch.setattr(gh_api, "_get_repo_slug", lambda _: "me/project", raising=True)
    monkeypatch.setattr(
        gh_api, "_push_current_branch", lambda _: "feature-branch", raising=True
    )

    # Fake GitHub response
    fake_resp = SimpleNamespace(
        status_code=201, json=lambda: {"html_url": "https://github.com/me/project/pull/1"}
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


def test_create_pr_github_error(monkeypatch, tmp_path: Path):
    """Non-2xx GitHub response should raise GitHubAPIError."""
    monkeypatch.setattr(gh_api, "is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr(gh_api, "get_github_token", lambda: "tok", raising=True)
    monkeypatch.setattr(
        gh_api, "_get_repo_slug", lambda _: "me/project", raising=True
    )
    monkeypatch.setattr(
        gh_api, "_push_current_branch", lambda _: "feature-branch", raising=True
    )

    bad_resp = SimpleNamespace(status_code=422, text="boom", json=lambda: {})
    with patch("requests.post", return_value=bad_resp):
        with pytest.raises(gh_api.GitHubAPIError):
            gh_api.create_pull_request("x", "y", repo_path=tmp_path)
