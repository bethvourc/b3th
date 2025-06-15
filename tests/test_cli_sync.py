"""Tests for the `b3th sync` command."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from typer.testing import CliRunner

from b3th.cli import app

runner = CliRunner()


def test_sync_full_flow(monkeypatch, tmp_path: Path):
    """
    Ensure sync runs git add, commit, and push in order.
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Pretend it's a git repo
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda _: True, raising=True)
    monkeypatch.setattr("b3th.cli.get_current_branch", lambda _: "feat-x", raising=True)

    # Stub generate_commit_message
    monkeypatch.setattr(
        "b3th.cli.generate_commit_message",
        lambda *_: ("feat: greet", "add friendly greeting"),
        raising=True,
    )

    # Capture subprocess calls
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("b3th.cli.subprocess.run", fake_run, raising=True)

    result = runner.invoke(app, ["sync", str(repo), "-y"])
    assert result.exit_code == 0

    assert ["git", "add", "--all"] in calls
    assert ["git", "commit", "-m", "feat: greet", "-m", "add friendly greeting"] in calls
    assert ["git", "push", "-u", "origin", "feat-x"] in calls
