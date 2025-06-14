"""Tests for the `b3th commit` command."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from typer.testing import CliRunner

from b3th.cli import app

runner = CliRunner()


def test_commit_happy_path(monkeypatch, tmp_path: Path):
    """
    End-to-end happy path with stubs:

    * generate_commit_message returns a deterministic subject/body
    * subprocess.run for git commit succeeds
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Pretend it's a git repo
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda _: True, raising=True)

    # Stub message generation
    monkeypatch.setattr(
        "b3th.cli.generate_commit_message",
        lambda _: ("feat(core): add X", "Add feature X with full details."),
        raising=True,
    )

    # Capture the args passed to subprocess.run
    captured = {}

    def fake_run(args, **kwargs):  # noqa: D401
        captured["args"] = args
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("b3th.cli.subprocess.run", fake_run, raising=True)

    result = runner.invoke(app, ["commit", str(repo), "-y"])
    assert result.exit_code == 0
    assert "✅ Commit created." in result.output

    # Verify git commit invocation
    assert captured["args"] == [
        "git",
        "commit",
        "-m",
        "feat(core): add X",
        "-m",
        "Add feature X with full details.",
    ]
