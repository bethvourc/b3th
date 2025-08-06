"""
Unit-tests for conflict_resolver helper functions.
"""

from pathlib import Path
import subprocess

from b3th.conflict_resolver import (
    list_conflicted_files,
    extract_conflict_hunks,
    build_resolution_prompt,
)


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


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _init_repo(repo: Path) -> None:
    """Initialise a bare Git repo with user identity configured."""
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)  # noqa: S603
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=repo, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Tester"], cwd=repo, check=True
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_conflict_listing(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    _init_repo(repo)

    (repo / "file.txt").write_text(_CONFLICT_TEXT)

    # Track the file so `git grep` can see it
    subprocess.run(["git", "add", "."], cwd=repo, check=True)  # noqa: S603
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True)

    conflicted = list_conflicted_files(repo)
    assert conflicted == [repo / "file.txt"]


def test_extract_hunks(tmp_path: Path) -> None:
    f = tmp_path / "c.txt"
    f.write_text(_CONFLICT_TEXT)
    hunks = extract_conflict_hunks(f)
    assert len(hunks) == 2
    assert hunks[0]["left"].strip() == "ours-a"
    assert hunks[0]["right"].strip() == "theirs-a"


def test_build_prompt(tmp_path: Path) -> None:
    repo = tmp_path / "r2"
    repo.mkdir()
    _init_repo(repo)
    (repo / "f.txt").write_text(_CONFLICT_TEXT)

    subprocess.run(["git", "add", "."], cwd=repo, check=True)  # noqa: S603
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True)

    prompt = build_resolution_prompt(repo)
    assert prompt is not None
    assert f"## File: `{repo / 'f.txt'}`" in prompt
    assert "### Conflict 2" in prompt
    assert "ours-b" in prompt and "theirs-b" in prompt
