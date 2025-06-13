from pathlib import Path
import subprocess

from b3th import git_utils


def test_git_utils_end_to_end(tmp_path: Path) -> None:
    """
    Create a temp repo, stage a file, and ensure helper functions behave.
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True)  # type: ignore[arg-type]

    # Create and stage a file
    sample = repo / "sample.txt"
    sample.write_text("hello\n")
    subprocess.run(["git", "add", "sample.txt"], cwd=repo, check=True)  # type: ignore[arg-type]

    # Assertions
    assert git_utils.is_git_repo(repo) is True

    branch = git_utils.get_current_branch(repo)
    # Git 2.28+ defaults to 'main'; older versions use 'master'
    assert branch in {"main", "master"}

    diff = git_utils.get_staged_diff(repo)
    assert "+hello" in diff  # diff should include added line
