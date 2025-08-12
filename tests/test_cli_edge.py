from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from b3th.cli import app
from b3th.commit_message import CommitMessageError
from b3th.pr_description import PRDescriptionError
from b3th.gh_api import GitHubAPIError, GitRepoError

runner = CliRunner()


def test_sync_commit_message_error(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)

    # git add succeeds so we reach the generator error
    monkeypatch.setattr(
        "b3th.cli.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=0),
        raising=True,
    )

    def boom(_repo):
        raise CommitMessageError("LLM unavailable")

    monkeypatch.setattr("b3th.cli.generate_commit_message", boom, raising=True)

    res = runner.invoke(app, ["sync", str(repo), "-y"])
    assert res.exit_code != 0
    assert "LLM unavailable" in res.output


def test_sync_git_commit_failure(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo2"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(
        "b3th.cli.generate_commit_message",
        lambda *_: ("subject", "body"),
        raising=True,
    )

    # First call (git add) -> 0, second (git commit) -> 1
    calls = {"n": 0}

    def fake_run(args, **kwargs):
        calls["n"] += 1
        return SimpleNamespace(returncode=0 if calls["n"] == 1 else 1)

    monkeypatch.setattr("b3th.cli.subprocess.run", fake_run, raising=True)

    res = runner.invoke(app, ["sync", str(repo), "-y"])
    assert res.exit_code != 0
    assert "git commit failed." in res.output


def test_sync_git_push_failure(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo3"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr("b3th.cli.get_current_branch", lambda *_: "feat-x", raising=True)
    monkeypatch.setattr(
        "b3th.cli.generate_commit_message",
        lambda *_: ("s", "b"),
        raising=True,
    )

    # add -> 0, commit -> 0, push -> 1
    def fake_run(args, **kwargs):
        if args[:3] == ["git", "add", "--all"]:
            return SimpleNamespace(returncode=0)
        if args[:2] == ["git", "commit"]:
            return SimpleNamespace(returncode=0)
        if args[:3] == ["git", "push", "-u"]:
            return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("b3th.cli.subprocess.run", fake_run, raising=True)

    res = runner.invoke(app, ["sync", str(repo), "-y"])
    assert res.exit_code != 0
    assert "git push failed" in res.output


def test_prcreate_description_error(monkeypatch, tmp_path: Path):
    repo = tmp_path / "rdesc"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)

    def boom(*_a, **_k):
        raise PRDescriptionError("no diffs")

    monkeypatch.setattr("b3th.cli.generate_pr_description", boom, raising=True)

    res = runner.invoke(app, ["prcreate", str(repo), "-y"])
    assert res.exit_code != 0
    assert "no diffs" in res.output


def test_prcreate_api_error(monkeypatch, tmp_path: Path):
    repo = tmp_path / "rapi"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(
        "b3th.cli.generate_pr_description",
        lambda *_a, **_k: ("T", "B"),
        raising=True,
    )

    def gh_boom(*_a, **_k):
        raise GitHubAPIError("bad token")

    monkeypatch.setattr("b3th.cli.create_pull_request", gh_boom, raising=True)

    res = runner.invoke(app, ["prcreate", str(repo), "-y"])
    assert res.exit_code != 0
    assert "bad token" in res.output


def test_prdraft_repo_error(monkeypatch, tmp_path: Path):
    repo = tmp_path / "rrepo"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.is_git_repo", lambda *_: True, raising=True)
    monkeypatch.setattr(
        "b3th.cli.generate_pr_description",
        lambda *_a, **_k: ("T", "B"),
        raising=True,
    )

    def repo_boom(*_a, **_k):
        raise GitRepoError("not a GH repo")

    monkeypatch.setattr("b3th.cli.create_draft_pull_request", repo_boom, raising=True)

    res = runner.invoke(app, ["prdraft", str(repo), "-y"])
    assert res.exit_code != 0
    assert "not a GH repo" in res.output


def test_resolve_no_conflicts_parsed(monkeypatch, tmp_path: Path):
    """Conflicts exist but resolver returns empty list → abort path."""
    repo = tmp_path / "rmerge"; repo.mkdir()
    monkeypatch.setattr("b3th.cli.has_merge_conflicts", lambda *_: True, raising=True)
    monkeypatch.setattr(
        "b3th.cli.resolve_conflicts", lambda *_a, **_k: [], raising=True
    )

    res = runner.invoke(app, ["resolve", str(repo)])
    assert res.exit_code != 0
    assert "No conflicts parsed" in res.output
