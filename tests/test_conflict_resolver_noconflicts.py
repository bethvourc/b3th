from pathlib import Path

from b3th.conflict_resolver import build_resolution_prompt, resolve_conflicts


def test_build_prompt_none_when_no_conflicts(tmp_path: Path) -> None:
    """Non-repo or clean repo => None prompt."""
    # Not a git repo → list_conflicted_files() returns []
    assert build_resolution_prompt(tmp_path) is None


def test_resolve_conflicts_returns_empty_on_clean_dir(tmp_path: Path) -> None:
    """Non-repo or clean repo → nothing to resolve."""
    assert resolve_conflicts(tmp_path) == []
