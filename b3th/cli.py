"""b3th CLI.

Run `poetry run b3th --help` to see available commands.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Load environment variables early 
from dotenv import load_dotenv

load_dotenv()  # reads .env in project root (if present)

import typer  # noqa: E402  (import after dotenv so env vars are ready)

from .commit_message import CommitMessageError, generate_commit_message
from .git_utils import is_git_repo
from .pr_description import PRDescriptionError, generate_pr_description
from .gh_api import (
    create_pull_request,
    GitHubAPIError,
    GitRepoError,
)  # noqa: E402  (after dotenv)

app = typer.Typer(
    help="Generate AI-assisted commit messages and GitHub PR descriptions."
)

# commit command
@app.command()
def commit(
    repo: Path = typer.Argument(
        Path("."), exists=False, dir_okay=True, file_okay=False, writable=True
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation and commit immediately.",
    ),
) -> None:
    """
    Generate a commit message from staged changes and create the commit.
    """
    if not is_git_repo(repo):
        typer.secho("Error: not inside a Git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        subject, body = generate_commit_message(repo)
    except CommitMessageError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("\nProposed commit message:")
    typer.echo(typer.style(subject, fg=typer.colors.GREEN, bold=True))
    if body:
        typer.echo("\n" + body)

    if not yes:
        if not typer.confirm("\nProceed with git commit?"):
            typer.echo("Cancelled – no commit created.")
            raise typer.Exit()

    args: list[str] = ["git", "commit", "-m", subject]
    if body:
        args.extend(["-m", body])

    result = subprocess.run(args)  # noqa: S603,S607  (trusted local call)
    if result.returncode != 0:
        typer.secho("git commit failed.", fg=typer.colors.RED)
        raise typer.Exit(result.returncode)

    typer.secho("✅ Commit created.", fg=typer.colors.GREEN)



# prcreate command


@app.command()
def prcreate(
    repo: Path = typer.Argument(
        Path("."), exists=False, dir_okay=True, file_okay=False, writable=True
    ),
    base: str = typer.Option(
        "main",
        "--base",
        "-b",
        help="Base branch to merge into (default: main).",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation and open PR immediately.",
    ),
) -> None:
    """
    Generate a pull-request title/body and open the PR on GitHub.
    """
    if not is_git_repo(repo):
        typer.secho("Error: not inside a Git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 1: Let the LLM craft the PR description
    try:
        title, body = generate_pr_description(repo, base=base)
    except PRDescriptionError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("\nProposed pull-request:")
    typer.echo(typer.style(title, fg=typer.colors.GREEN, bold=True))
    typer.echo("\n" + body)

    if not yes:
        if not typer.confirm("\nProceed to create PR on GitHub?"):
            typer.echo("Cancelled – no pull-request created.")
            raise typer.Exit()

    # Step 2: Call GitHub API
    try:
        pr_url = create_pull_request(title, body, repo_path=repo, base=base)
    except (GitRepoError, GitHubAPIError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("\n✅ Pull request created!", fg=typer.colors.GREEN, bold=True)
    typer.echo(pr_url)


if __name__ == "__main__":
    app()
