"""b3th CLI skeleton (Step 3).

Run `poetry run b3th --help` to see available commands.
"""

import typer

app = typer.Typer(
    help="Generate AI-assisted commit messages and GitHub PR descriptions."
)


@app.command()
def commit() -> None:
    """Generate and apply a commit message (placeholder)."""
    typer.echo("🔧 TODO: implement commit-message generation in later steps.")


@app.command()
def prcreate() -> None:
    """Generate a pull-request description and open the PR (placeholder)."""
    typer.echo("🔧 TODO: implement PR creation in later steps.")


if __name__ == "__main__":
    app()
