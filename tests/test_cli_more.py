from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from b3th.cli import app

runner = CliRunner()


def test_sync_cancel(monkeypatch, tmp_path: Path):
    """User declines the confirmation; only git add is called."""
    repo = tmp_path / "r"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr("b3th.cli.generate_commit_message", lambda *_: ("t", "b"), raising=True)
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("b3th.cli.subprocess.run", fake_run, raising=True)
    monkeypatch.setattr("b3th.cli.typer.confirm", lambda *_: False, raising=True)

    res = runner.invoke(app, ["sync", str(repo)])
    assert res.exit_code == 0
    assert "Cancelled – nothing committed." in res.output
    assert ["git", "add", "--all"] in calls
    assert not any(cmd[:2] == ["git", "commit"] for cmd in calls)


def test_sync_git_add_failure(monkeypatch, tmp_path: Path):
    """git add fails → we show message and exit non-zero."""
    repo = tmp_path / "r2"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)

    def fake_run(args, **kwargs):
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr("b3th.cli.subprocess.run", fake_run, raising=True)

    res = runner.invoke(app, ["sync", str(repo), "-y"])
    assert res.exit_code != 0
    assert "git add failed." in res.output


def test_prcreate_cancel(monkeypatch, tmp_path: Path):
    """User cancels regular PR creation at the confirmation step."""
    repo = tmp_path / "r3"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr("b3th.cli.generate_pr_description", lambda *_a, **_k: ("T", "B"), raising=True)
    monkeypatch.setattr("b3th.cli.typer.confirm", lambda *_: False, raising=True)

    res = runner.invoke(app, ["prcreate", str(repo)])
    assert res.exit_code == 0
    assert "Cancelled – no PR created." in res.output


def test_prdraft_cancel(monkeypatch, tmp_path: Path):
    """User cancels draft PR creation at the confirmation step."""
    repo = tmp_path / "r4"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr("b3th.cli.generate_pr_description", lambda *_a, **_k: ("T", "B"), raising=True)
    monkeypatch.setattr("b3th.cli.typer.confirm", lambda *_: False, raising=True)

    res = runner.invoke(app, ["prdraft", str(repo)])
    assert res.exit_code == 0
    assert "Cancelled – no draft PR created." in res.output


def test_prcreate_not_repo(monkeypatch, tmp_path: Path):
    """Non-repo path should error before trying to generate a PR."""
    repo = tmp_path / "nope"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: False, raising=True)

    res = runner.invoke(app, ["prcreate", str(repo), "-y"])
    assert res.exit_code != 0
    assert "Not inside a Git repository" in res.output


def test_prdraft_not_repo(monkeypatch, tmp_path: Path):
    """Non-repo path should error before trying to generate a draft PR."""
    repo = tmp_path / "nope2"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: False, raising=True)

    res = runner.invoke(app, ["prdraft", str(repo), "-y"])
    assert res.exit_code != 0
    assert "Not inside a Git repository" in res.output


def test_resolve_no_conflicts(monkeypatch, tmp_path: Path):
    """Resolve exits cleanly when no conflicts are detected."""
    repo = tmp_path / "r5"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.has_merge_conflicts", lambda *_: False, raising=True)

    res = runner.invoke(app, ["resolve", str(repo)])
    assert res.exit_code == 0
    assert "No unresolved conflicts detected." in res.output


def test_commit_deprecated_alias(monkeypatch, tmp_path: Path):
    """
    The deprecated `commit` command proxies to `sync`.
    Exercise the fallback branch when current branch is None → uses 'feat-x'.
    """
    repo = tmp_path / "r6"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr("b3th.cli.generate_commit_message", lambda *_: ("t", "b"), raising=True)
    monkeypatch.setattr("b3th.cli.get_current_branch", lambda *_: None, raising=True)

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("b3th.cli.subprocess.run", fake_run, raising=True)

    res = runner.invoke(app, ["commit", str(repo), "-y"])
    assert res.exit_code == 0
    assert "deprecated" in res.output.lower()
    assert ["git", "push", "-u", "origin", "feat-x"] in calls
