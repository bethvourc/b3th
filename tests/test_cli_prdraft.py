"""Tests for the `b3th prdraft` command."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from typer.testing import CliRunner

from b3th.cli import app

runner = CliRunner()


def test_prdraft_happy(monkeypatch, tmp_path: Path):
    """Open a draft PR and echo URL."""
    repo = tmp_path / "repo"; repo.mkdir()

    # Pretend we are in a git repo
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)

    # Stub PR description
    monkeypatch.setattr(
        "b3th.cli.generate_pr_description",
        lambda *_a, **_k: ("WIP: feat X", "Draft body"),
        raising=True,
    )

    # Fake GitHub call
    def fake_create_draft(*_a, **_k):
        return "https://github.com/me/project/pull/123"

    monkeypatch.setattr(
        "b3th.cli.create_draft_pull_request", fake_create_draft, raising=True
    )

    res = runner.invoke(app, ["prdraft", str(repo), "-y"])
    assert res.exit_code == 0
    assert "Draft pull request created" in res.output
    assert "pull/123" in res.output
