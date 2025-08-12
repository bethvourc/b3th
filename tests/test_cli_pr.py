"""Tests for the `b3th prcreate` command."""

from pathlib import Path

from typer.testing import CliRunner

from b3th.cli import app

runner = CliRunner()


def test_prcreate_happy_path(monkeypatch, tmp_path: Path):
    """Happy path: PR is created and URL displayed."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Pretend it's a git repo
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda _: True, raising=True)

    # Stub PR description generator
    monkeypatch.setattr(
        "b3th.cli.generate_pr_description",
        lambda *_args, **_kw: ("add api", "Detailed body"),
        raising=True,
    )

    # Capture args sent to create_pull_request
    captured = {}

    def fake_create_pr(title, body, *, repo_path, base):
        captured["title"] = title
        captured["body"] = body
        captured["repo_path"] = repo_path
        captured["base"] = base
        return "https://github.com/me/project/pull/42"

    monkeypatch.setattr("b3th.cli.create_pull_request", fake_create_pr, raising=True)

    result = runner.invoke(app, ["prcreate", str(repo), "-y"])
    assert result.exit_code == 0
    assert "Pull request created" in result.output
    assert "https://github.com/me/project/pull/42" in result.output
    assert captured["title"] == "add api"
    assert captured["base"] == "main"
