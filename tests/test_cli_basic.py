from typer.testing import CliRunner

from b3th.cli import app

runner = CliRunner()


def test_help_runs() -> None:
    """`b3th --help` should exit cleanly and list the main commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # basic sanity checks
    assert "commit" in result.output
    assert "prcreate" in result.output
