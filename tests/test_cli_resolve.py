"""
CLI integration test for `b3th resolve`.
"""

from pathlib import Path
from typer.testing import CliRunner

from b3th.cli import app

runner = CliRunner()


def test_resolve_creates_files(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo"; repo.mkdir()

    # Pretend repo has conflicts
    monkeypatch.setattr("b3th.cli.has_merge_conflicts", lambda *_: True, raising=True)

    # Stub resolve_conflicts: pretend it created two files
    resolved = [
        repo / "a.txt.resolved",
        repo / "b.txt.resolved",
    ]
    for p in resolved:
        p.write_text("merged\n")

    monkeypatch.setattr("b3th.cli.resolve_conflicts", lambda *_a, **_k: resolved, raising=True)

    result = runner.invoke(app, ["resolve", str(repo)])
    assert result.exit_code == 0
    assert "Generated 2 *.resolved file" in result.stdout


def test_resolve_apply_overwrites(monkeypatch, tmp_path: Path):
    repo = tmp_path / "r2"; repo.mkdir()
    orig = repo / "x.txt"; orig.write_text("<<<<<<<")          # dummy

    # Fake conflict detection + resolver
    monkeypatch.setattr("b3th.cli.has_merge_conflicts", lambda *_: True, raising=True)
    resolved_path = orig.with_suffix(".txt.resolved")
    resolved_path.write_text("merged\n")
    monkeypatch.setattr("b3th.cli.resolve_conflicts", lambda *_a, **_k: [resolved_path], raising=True)

    res = runner.invoke(app, ["resolve", str(repo), "--apply"])
    assert res.exit_code == 0
    # original file replaced with merged content
    assert orig.read_text() == "merged\n"
    # *.resolved removed
    assert not resolved_path.exists()
