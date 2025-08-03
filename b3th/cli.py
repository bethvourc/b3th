"""b3th CLI.

Run `poetry run b3th --help` to see available commands.
"""

from __future__ import annotations

# Early-load compatibility patch
from ._compat import patch_click_make_metavar

patch_click_make_metavar()

import subprocess
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # auto-load .env before other imports

import typer  # noqa: E402

from .commit_message import CommitMessageError, generate_commit_message
from .git_utils import get_current_branch, is_git_repo
from .pr_description import PRDescriptionError, generate_pr_description
from .gh_api import (
    create_pull_request,
    create_draft_pull_request,
    GitHubAPIError,
    GitRepoError,
)
from .stats import get_stats
from .summarizer import summarize_commits

app = typer.Typer(
    help="Generate AI-assisted commits, sync, and pull-requests."
)


# sync  (stage → commit → push)
@app.command(name="sync")
def sync(
    repo: Path = typer.Argument(
        Path("."), exists=False, dir_okay=True, file_okay=False, writable=True
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation and run non-interactively.",
    ),
) -> None:
    """
    Stage all changes, generate an AI commit message, commit, and push the
    current branch to `origin`.
    """
    if not is_git_repo(repo):
        typer.secho("Error: not inside a Git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # git add --all
    res = subprocess.run(["git", "add", "--all"], cwd=repo)  # noqa: S603,S607
    if res.returncode != 0:
        typer.secho("git add failed.", fg=typer.colors.RED)
        raise typer.Exit(res.returncode)

    # Generate commit message
    try:
        subject, body = generate_commit_message(repo)
    except CommitMessageError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("\nProposed commit message:")
    typer.echo(typer.style(subject, fg=typer.colors.GREEN, bold=True))
    if body:
        typer.echo("\n" + body)

    if not yes and not typer.confirm("\nProceed with commit & push?"):
        typer.echo("Cancelled – nothing committed.")
        raise typer.Exit()

    # git commit
    args: list[str] = ["git", "commit", "-m", subject]
    if body:
        args.extend(["-m", body])

    res = subprocess.run(args, cwd=repo)  # noqa: S603,S607
    if res.returncode != 0:
        typer.secho("git commit failed.", fg=typer.colors.RED)
        raise typer.Exit(res.returncode)

    # git push
    branch = get_current_branch(repo)
    push_res = subprocess.run(
        ["git", "push", "-u", "origin", branch], cwd=repo  # noqa: S603,S607
    )
    if push_res.returncode != 0:
        typer.secho(
            "git push failed. Does 'origin' exist and is authentication set?",
            fg=typer.colors.RED,
        )
        raise typer.Exit(push_res.returncode)

    typer.secho("💻 Synced! Commit pushed to origin.", fg=typer.colors.GREEN)

# DEPRECATED: commit  (proxy to sync)
@app.command(hidden=True)
def commit(*args, **kwargs):  # noqa: ANN001
    """DEPRECATED – use `b3th sync`."""
    typer.secho(
        "Warning: `b3th commit` is deprecated. Use `b3th sync` instead.",
        fg=typer.colors.YELLOW,
    )
    sync(*args, **kwargs)  # delegate


# stats
@app.command()
def stats(
    repo: Path = typer.Argument(
        Path("."), exists=False, dir_okay=True, file_okay=False
    ),
    last: str | None = typer.Option(
        None,
        "--last",
        "-l",
        help="Time-frame (e.g. 7d, 1m).",
    ),
) -> None:
    """Show repository statistics."""
    from .stats import print_stats  # local import to avoid CLI startup cost

    print_stats(repo, last=last)


# summarize
@app.command(name="summarize")
def summarize(
    repo: Path = typer.Argument(
        Path("."), exists=False, dir_okay=True, file_okay=False
    ),
    n: int = typer.Option(
        10,
        "--last",
        "-n",
        help="Number of commits to summarize (default: 10).",
    ),
) -> None:
    """Summarize the last *n* commits."""
    summary = summarize_commits(str(repo), n=n)
    typer.echo(summary or "summarizer feature not implemented yet. 🚧")


# prdraft  – open a draft PR
@app.command()
def prdraft(
    repo: Path = typer.Argument(
        Path("."), exists=False, dir_okay=True, file_okay=False, writable=True
    ),
    base: str = typer.Option("main", "--base", "-b", help="Target branch"),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation and open draft PR."
    ),
) -> None:
    """Open a **draft** pull request on GitHub."""
    if not is_git_repo(repo):
        typer.secho("Error: not inside a Git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        title, body = generate_pr_description(repo, base=base)
    except PRDescriptionError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("\nProposed draft PR:")
    typer.echo(typer.style(title, fg=typer.colors.GREEN, bold=True))
    typer.echo("\n" + body)

    if not yes and not typer.confirm("\nProceed to create *draft* PR on GitHub?"):
        typer.echo("Cancelled – no draft PR created.")
        raise typer.Exit()

    try:
        pr_url = create_draft_pull_request(title, body, repo_path=repo, base=base)
    except (GitRepoError, GitHubAPIError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("\n✅ Draft pull request created!", fg=typer.colors.GREEN, bold=True)
    typer.echo(pr_url)



# prcreate  – open a regular PR
@app.command()
def prcreate(
    repo: Path = typer.Argument(
        Path("."), exists=False, dir_okay=True, file_okay=False, writable=True
    ),
    base: str = typer.Option("main", "--base", "-b"),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Generate a pull request title/body and open the PR on GitHub."""
    if not is_git_repo(repo):
        typer.secho("Error: not inside a Git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        title, body = generate_pr_description(repo, base=base)
    except PRDescriptionError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("\nProposed pull request:")
    typer.echo(typer.style(title, fg=typer.colors.GREEN, bold=True))
    typer.echo("\n" + body)

    if not yes and not typer.confirm("\nProceed to create PR on GitHub?"):
        typer.echo("Cancelled – no PR created.")
        raise typer.Exit()

    try:
        pr_url = create_pull_request(title, body, repo_path=repo, base=base)
    except (GitRepoError, GitHubAPIError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("\n✅ Pull request created!", fg=typer.colors.GREEN, bold=True)
    typer.echo(pr_url)


if __name__ == "__main__":
    app()
