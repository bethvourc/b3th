"""b3th CLI.

Run `poetry run b3th --help` to see available commands.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

# Early-load compatibility patch
from ._compat import patch_click_make_metavar
from .commit_message import CommitMessageError, generate_commit_message
from .conflict_resolver import resolve_conflicts
from .gh_api import (
    GitHubAPIError,
    GitRepoError,
    create_draft_pull_request,
    create_pull_request,
)
from .git_utils import get_current_branch, has_merge_conflicts, is_git_repo
from .pr_description import PRDescriptionError, generate_pr_description
from .summarizer import summarize_commits

# Apply compatibility patch and load environment
patch_click_make_metavar()
load_dotenv()  # auto-load .env before other imports

app = typer.Typer(help="Generate AI-assisted commits, sync, and pull-requests.")

# Default argument values as module-level constants
DEFAULT_REPO = Path(".")
DEFAULT_YES = False
DEFAULT_BASE = "main"
DEFAULT_N = 10
DEFAULT_APPLY = False
DEFAULT_MODEL = None

# Typer argument objects as module-level constants
REPO_ARG = typer.Argument(
    DEFAULT_REPO, exists=False, dir_okay=True, file_okay=False, writable=True
)
REPO_ARG_READONLY = typer.Argument(
    DEFAULT_REPO, exists=False, dir_okay=True, file_okay=False
)
YES_OPTION = typer.Option(
    DEFAULT_YES,
    "--yes",
    "-y",
    help="Skip interactive confirmation and run non-interactively.",
)
BASE_OPTION = typer.Option(DEFAULT_BASE, "--base", "-b", help="Target branch")
BASE_OPTION_SIMPLE = typer.Option(DEFAULT_BASE, "--base", "-b")
N_OPTION = typer.Option(
    DEFAULT_N,
    "--last",
    "-n",
    help="Number of commits to summarize (default: 10).",
)
YES_OPTION_SIMPLE = typer.Option(DEFAULT_YES, "--yes", "-y")
APPLY_OPTION = typer.Option(
    DEFAULT_APPLY,
    "--apply",
    "-a",
    help="Overwrite original files with *.resolved output.",
)
MODEL_OPTION = typer.Option(
    DEFAULT_MODEL, "--model", "-m", help="LLM model ID passed through to the resolver."
)


# sync  (stage → commit → push)
@app.command(name="sync")
def sync(
    repo: Path = REPO_ARG,
    yes: bool = YES_OPTION,
) -> None:
    """
    Stage all changes, generate an AI commit message, commit, and push the
    current branch to `origin`.
    """
    if not is_git_repo(repo):
        typer.echo("Not inside a Git repository")
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
        raise typer.Exit(1) from exc

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
        ["git", "push", "-u", "origin", "feat-x" if branch is None else branch],
        cwd=repo,  # noqa: S603,S607
    )
    if push_res.returncode != 0:
        typer.secho(
            "git push failed. Does 'origin' exist and is authentication set?",
            fg=typer.colors.RED,
        )
        raise typer.Exit(push_res.returncode)

    typer.secho("💻 Synced! Commit pushed to origin.", fg=typer.colors.GREEN)


# commit (visible for help output; proxies to sync)
@app.command(help="(Deprecated) Use `b3th sync`. Provided for compatibility.")
def commit(
    repo: Path = REPO_ARG,
    yes: bool = YES_OPTION,
) -> None:
    """Deprecated alias for `sync` to keep help output stable."""
    typer.secho(
        "Warning: `b3th commit` is deprecated. Use `b3th sync` instead.",
        fg=typer.colors.YELLOW,
    )
    sync(repo=repo, yes=yes)


# stats
@app.command()
def stats(
    repo: Path = REPO_ARG_READONLY,
    last: Optional[str] = typer.Option(
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
    repo: Path = REPO_ARG_READONLY,
    n: int = N_OPTION,
) -> None:
    """Summarize the last *n* commits."""
    summary = summarize_commits(str(repo), n=n)
    typer.echo(summary or "summarizer feature not implemented yet. 🚧")


# prdraft  – open a draft PR
@app.command()
def prdraft(
    repo: Path = REPO_ARG,
    base: str = BASE_OPTION,
    yes: bool = YES_OPTION_SIMPLE,
) -> None:
    """Open a **draft** pull request on GitHub."""
    if not is_git_repo(repo):
        typer.echo("Not inside a Git repository")
        raise typer.Exit(1)

    try:
        title, body = generate_pr_description(repo, base=base)
    except PRDescriptionError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1) from exc

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
        raise typer.Exit(1) from exc

    typer.secho("Draft pull request created", fg=typer.colors.GREEN, bold=True)
    typer.echo(pr_url)


# prcreate  – open a regular PR
@app.command()
def prcreate(
    repo: Path = REPO_ARG,
    base: str = BASE_OPTION_SIMPLE,
    yes: bool = YES_OPTION_SIMPLE,
) -> None:
    """Generate a pull request title/body and open the PR on GitHub."""
    if not is_git_repo(repo):
        typer.echo("Not inside a Git repository")
        raise typer.Exit(1)

    try:
        title, body = generate_pr_description(repo, base=base)
    except PRDescriptionError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1) from exc

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
        raise typer.Exit(1) from exc

    typer.secho("Pull request created", fg=typer.colors.GREEN, bold=True)
    typer.echo(pr_url)


# resolve – ask the LLM to propose merged versions
@app.command()
def resolve(  # noqa: D401
    repo: Path = REPO_ARG_READONLY,
    apply: bool = APPLY_OPTION,
    model: Optional[str] = MODEL_OPTION,
) -> None:
    """
    Generate merge-conflict resolutions using the configured LLM.

    Without *--apply* it only creates `<file>.resolved` siblings.
    """
    if not has_merge_conflicts(repo):
        typer.echo("No unresolved conflicts detected.")
        raise typer.Exit()

    typer.echo("Detecting conflicts & asking Groq…")
    out_paths = resolve_conflicts(repo, model=model)

    if not out_paths:
        typer.secho("No conflicts parsed — aborting.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"💡 Generated {len(out_paths)} *.resolved file(s).")

    if apply:
        for p in out_paths:
            # Strip only the trailing ".resolved"
            original = Path(str(p))
            if original.name.endswith(".resolved"):
                original = Path(str(original)[: -len(".resolved")])
            else:
                original = p.with_suffix("")  # fallback

            original.write_text(Path(p).read_text())
            Path(p).unlink(missing_ok=True)
        typer.secho(
            "Originals overwritten with proposed merges.", fg=typer.colors.GREEN
        )
    else:
        typer.echo("Inspect the *.resolved files. Re-run with --apply to accept.")


if __name__ == "__main__":
    app()
