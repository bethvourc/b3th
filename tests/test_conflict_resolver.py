"""
Tests for conflict_resolver: listing, hunk extraction, Groq-powered resolution.
"""

import subprocess
from pathlib import Path

import b3th.conflict_resolver as cr

_CONFLICT_TEXT = """\
line-1
<<<<<<< HEAD
ours-a
=======
theirs-a
>>>>>>> feature
line-2
<<<<<<< HEAD
ours-b
=======
theirs-b
>>>>>>> feature
"""


# helpers
def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)  # noqa: S603,S607
    subprocess.run(["git", "config", "user.email", "t@x"], cwd=repo, check=True)  # noqa: S603,S607
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)  # noqa: S603,S607


def _seed_conflict(repo: Path, fname: str = "file.txt") -> Path:
    f = repo / fname
    f.write_text(_CONFLICT_TEXT)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)  # noqa: S603,S607
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True)  # noqa: S603,S607
    return f


# tests


def test_conflict_listing(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _init_repo(repo)
    path = _seed_conflict(repo)
    assert cr.list_conflicted_files(repo) == [path]


def test_extract_hunks(tmp_path: Path) -> None:
    f = tmp_path / "c.txt"
    f.write_text(_CONFLICT_TEXT)
    hunks = cr.extract_conflict_hunks(f)
    assert len(hunks) == 2
    assert hunks[1]["left"].strip() == "ours-b"


def test_build_prompt(tmp_path: Path) -> None:
    repo = tmp_path / "r2"
    repo.mkdir()
    _init_repo(repo)
    path = _seed_conflict(repo, "f.txt")
    prompt = cr.build_resolution_prompt(repo)
    assert prompt and path.name in prompt and "### Conflict 2" in prompt


def test_llm_resolution(tmp_path: Path, monkeypatch) -> None:
    """LLM output is written to <file>.resolved."""
    repo = tmp_path / "r3"
    repo.mkdir()
    _init_repo(repo)
    path = _seed_conflict(repo, "conf.txt")

    # Stub chat_completion
    stub_output = "merged\ncode\n"
    monkeypatch.setattr(cr, "chat_completion", lambda prompt, model=None: stub_output)

    out_paths = cr.resolve_conflicts(repo, model="gpt-mock")
    expected_out = path.with_suffix(".txt.resolved")

    assert out_paths == [expected_out]
    assert expected_out.read_text() == stub_output
