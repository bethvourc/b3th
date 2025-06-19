"""
GitHub REST helpers.

Provides a minimal wrapper around GitHub's v3 REST API so higher-level code
(e.g., the CLI) can create branches, push them, and open pull requests without
duplicating logic.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

import requests

from .config import ConfigError, get_github_token
from .git_utils import GitError, get_current_branch, is_git_repo


# Exceptions


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub API returns a non-2xx response."""


class GitRepoError(RuntimeError):
    """Raised when local git operations fail."""


# Internal git helpers
def _run_git(args: list[str], cwd: Path | str | None = None) -> str:
    """Run `git <args>` and return stdout (strip newline)."""
    result = subprocess.run(  # noqa: S603,S607
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitRepoError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _slug_from_remote(url: str) -> str:
    """
    Convert a remote URL to ``owner/repo`` form.

    Handles:
    - git@github.com:owner/repo.git
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo
    """
    # Strip trailing .git
    url = url.rstrip(".git")

    # SSH
    m = re.match(r"git@github\.com:(?P<slug>.+/.+)$", url)
    if m:
        return m.group("slug")

    # HTTPS
    m = re.match(r"https://github\.com/(?P<slug>.+/.+)$", url)
    if m:
        return m.group("slug")

    raise GitRepoError(f"Cannot parse GitHub remote URL: {url}")


def _get_repo_slug(path: Path | str) -> str:
    """Return ``owner/repo`` for the given working tree."""
    remote_url = _run_git(["config", "--get", "remote.origin.url"], cwd=path)
    return _slug_from_remote(remote_url)


def _push_current_branch(path: Path | str) -> str:
    """Push the current branch to origin and return its name."""
    branch = get_current_branch(path)
    _run_git(["push", "-u", "origin", branch], cwd=path)
    return branch


# Public API
def create_pull_request(
    title: str,
    body: str,
    *,
    repo_path: Path | str = ".",
    base: str = "main",
    head: str | None = None,
) -> str:
    """
    Open a GitHub pull request and return its HTML URL.

    Parameters
    ----------
    title
        PR title.
    body
        PR body (markdown).
    repo_path
        Local git repository path.
    base
        Base branch to merge into (default = ``main``).
    head
        Head branch to merge from.  If ``None``, the current branch is pushed.

    Raises
    ------
    ConfigError, GitRepoError, GitHubAPIError
    """
    repo_path = Path(repo_path)

    if not is_git_repo(repo_path):
        raise GitRepoError(f"{repo_path} is not a Git repository")

    token = get_github_token()  # may raise ConfigError

    # Ensure branch is present on origin
    head_branch = head or _push_current_branch(repo_path)

    slug = _get_repo_slug(repo_path)
    url = f"https://api.github.com/repos/{slug}/pulls"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload: Mapping[str, Any] = {
        "title": title,
        "head": head_branch,
        "base": base,
        "body": body,
        "maintainer_can_modify": True,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        raise GitHubAPIError(f"GitHub API error {resp.status_code}: {resp.text}")

    data = resp.json()
    html_url = data.get("html_url")
    if not html_url:
        raise GitHubAPIError("GitHub response missing html_url field")

    return str(html_url)


# --------------------------------------------------------------------------- #
# Draft PR helper
# --------------------------------------------------------------------------- #
def create_draft_pull_request(
    title: str,
    body: str,
    *,
    repo_path: Path | str = ".",
    base: str = "main",
    head: str | None = None,
) -> str:
    """
    Same as ``create_pull_request`` but opens the PR in **draft** mode.

    Returns
    -------
    str
        HTML URL of the new draft pull-request.
    """
    repo_path = Path(repo_path)

    if not is_git_repo(repo_path):
        raise GitRepoError(f"{repo_path} is not a Git repository")

    token = get_github_token()

    # Ensure branch is present on origin
    head_branch = head or _push_current_branch(repo_path)

    slug = _get_repo_slug(repo_path)
    url = f"https://api.github.com/repos/{slug}/pulls"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload: Mapping[str, Any] = {
        "title": title,
        "head": head_branch,
        "base": base,
        "body": body,
        "draft": True,                 # key difference
        "maintainer_can_modify": True,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        raise GitHubAPIError(f"GitHub API error {resp.status_code}: {resp.text}")

    data = resp.json()
    html_url = data.get("html_url")
    if not html_url:
        raise GitHubAPIError("GitHub response missing html_url field")

    return str(html_url)