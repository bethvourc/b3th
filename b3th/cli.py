"""b3th CLI.

Run `poetry run b3th --help` to see available commands.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

# Load environment variables 
from dotenv import load_dotenv

load_dotenv()  # reads .env in project root (if present) before other imports

import typer  # noqa: E402  (imported after dotenv so env vars are ready)

from .commit_message import CommitMessageError, generate_commit_message
from .git_utils import is_git_repo

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

    Example:

        b3th commit             # interactive confirm
        b3th commit -y          # non-interactive
    """
    # Ensure we are inside a Git repository
    if not is_git_repo(repo):
        typer.secho("Error: not inside a Git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Ask the LLM for a message
    try:
        subject, body = generate_commit_message(repo)
    except CommitMessageError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Show the proposed message
    typer.echo("\nProposed commit message:")
    typer.echo(typer.style(subject, fg=typer.colors.GREEN, bold=True))
    if body:
        typer.echo("\n" + body)

    # Confirm with the user unless --yes provided
    if not yes:
        proceed = typer.confirm("\nProceed with git commit?")
        if not proceed:
            typer.echo("Cancelled – no commit created.")
            raise typer.Exit()

    # Build git commit command
    args: list[str] = ["git", "commit", "-m", subject]
    if body:
        args.extend(["-m", body])

    result = subprocess.run(args)  # noqa: S603,S607  (trusted local call)
    if result.returncode != 0:
        typer.secho("git commit failed.", fg=typer.colors.RED)
        raise typer.Exit(result.returncode)

    typer.secho("✅ Commit created.", fg=typer.colors.GREEN)



# prcreate (stub) – implement in later steps
@app.command()
def prcreate() -> None:
    """Generate a pull-request description and open the PR (placeholder)."""
    typer.echo("🔧 TODO: implement PR creation in later steps.")


if __name__ == "__main__":
    app()
