"""
GitHub REST helpers.

Provides a minimal wrapper around GitHub's v3 REST API so higher-level code
(e.g., the CLI) can create branches, push them, and open pull requests without
duplicating logic.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import requests

from .config import ConfigError, get_github_token
from .git_utils import get_current_branch, is_git_repo


# Exceptions
class GitHubAPIError(RuntimeError):
    """Raised when the GitHub API or gh CLI returns a failure."""


class GitRepoError(RuntimeError):
    """Raised when local git operations fail."""


# --------------------------------------------------------------------------- #
# Executable resolvers (avoid S607 by using absolute paths)
# --------------------------------------------------------------------------- #
def _git_exe() -> str:
    """Return absolute path to the git executable."""
    path = shutil.which("git")
    if not path:
        raise GitRepoError("git executable not found in PATH")
    return path


def _gh_exe() -> str:
    """Return absolute path to the GitHub CLI executable."""
    path = shutil.which("gh")
    if not path:
        raise GitHubAPIError("GitHub CLI (gh) not found in PATH")
    return path


# --------------------------------------------------------------------------- #
# Internal: git helpers
# --------------------------------------------------------------------------- #
def _run_git(args: list[str], cwd: Path | str | None = None) -> str:
    """Run `git <args>` and return stdout (strip newline)."""
    result = subprocess.run(  # noqa: S603 (intentional external command)
        [_git_exe(), *args],
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
    # Strip a single trailing ".git" if present (avoid str.rstrip bug)
    if url.endswith(".git"):
        url = url[:-4]

    # SSH
    m = re.match(r"^git@github\.com:(?P<slug>[^/]+/[^/]+)$", url)
    if m:
        return m.group("slug")

    # HTTPS
    m = re.match(r"^https://github\.com/(?P<slug>[^/]+/[^/]+)$", url)
    if m:
        return m.group("slug")

    raise GitRepoError(f"Cannot parse GitHub remote URL: {url}")


def _get_repo_slug(path: str | Path) -> str:
    """Return ``owner/repo`` for the given working tree."""
    remote_url = _run_git(["config", "--get", "remote.origin.url"], cwd=path)
    return _slug_from_remote(remote_url)


def _push_current_branch(path: str | Path) -> str:
    """Push the current branch to origin and return its name."""
    branch = get_current_branch(path)
    _run_git(["push", "-u", "origin", branch], cwd=path)
    return branch


# --------------------------------------------------------------------------- #
# Internal: API plumbing
# --------------------------------------------------------------------------- #
def _api_base() -> str:
    # Allow override (e.g., GHES): https://{hostname}/api/v3
    return os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/")


def _auth_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "b3th-cli",
    }
    if token:
        # GitHub supports either "token" or "Bearer"
        headers["Authorization"] = f"token {token}"
    return headers


def _requests_post(path: str, payload: Mapping[str, Any], token: str | None) -> dict:
    """POST using requests with optional PAT auth."""
    url = f"{_api_base().rstrip('/')}/{path.lstrip('/')}"
    headers = _auth_headers(token)
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise GitHubAPIError(f"Network error calling GitHub: {exc}") from exc

    if resp.status_code not in (200, 201):
        # Try to surface GitHub's message when possible
        try:
            msg = resp.json()
        except Exception:
            msg = resp.text
        raise GitHubAPIError(f"GitHub API error {resp.status_code}: {msg}")

    try:
        return resp.json()
    except Exception as exc:
        raise GitHubAPIError(f"Malformed GitHub response: {resp.text}") from exc


def _gh_cli_post(path: str, payload: Mapping[str, Any]) -> dict:
    """
    POST using `gh api` (reads JSON body from stdin). Requires `gh auth login`.
    """
    cmd = [
        _gh_exe(),
        "api",
        "-X",
        "POST",
        path,
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "Content-Type: application/json",
        "--input",
        "-",  # read JSON body from stdin
    ]
    proc = subprocess.run(  # noqa: S603 (intentional external command)
        cmd,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise GitHubAPIError(proc.stderr.strip() or f"`gh api {path}` failed")
    try:
        return json.loads(proc.stdout)
    except Exception as exc:
        raise GitHubAPIError(f"Malformed gh api response: {proc.stdout}") from exc


def _post_json(path: str, payload: Mapping[str, Any]) -> dict:
    """
    Try PAT via requests first; if no token present, fall back to `gh api`.
    """
    token: str | None
    try:
        # No kwargs: compatible with test stubs (monkeypatched no-arg lambda)
        token = get_github_token()
    except ConfigError:
        token = None

    if token:
        return _requests_post(path, payload, token)
    # No token provided: rely on user's gh CLI auth
    return _gh_cli_post(path, payload)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def create_pull_request(
    title: str,
    body: str,
    *,
    repo_path: str | Path = ".",
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
        Head branch to merge from. If ``None``, the current branch is pushed.

    Raises
    ------
    GitRepoError, GitHubAPIError
    """
    repo_path = Path(repo_path)
    if not is_git_repo(repo_path):
        raise GitRepoError(f"{repo_path} is not a Git repository")

    # Ensure branch is present on origin
    head_branch = head or _push_current_branch(repo_path)

    slug = _get_repo_slug(repo_path)
    payload: Mapping[str, Any] = {
        "title": title,
        "head": head_branch,
        "base": base,
        "body": body,
        "maintainer_can_modify": True,
    }
    data = _post_json(f"/repos/{slug}/pulls", payload)

    html_url = data.get("html_url")
    if not html_url:
        raise GitHubAPIError("GitHub response missing html_url field")
    return str(html_url)


def create_draft_pull_request(
    title: str,
    body: str,
    *,
    repo_path: str | Path = ".",
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

    # Ensure branch is present on origin
    head_branch = head or _push_current_branch(repo_path)

    slug = _get_repo_slug(repo_path)
    payload: Mapping[str, Any] = {
        "title": title,
        "head": head_branch,
        "base": base,
        "body": body,
        "draft": True,  # key difference
        "maintainer_can_modify": True,
    }
    data = _post_json(f"/repos/{slug}/pulls", payload)

    html_url = data.get("html_url")
    if not html_url:
        raise GitHubAPIError("GitHub response missing html_url field")
    return str(html_url)
