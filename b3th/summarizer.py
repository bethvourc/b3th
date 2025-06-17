"""
summarizer.py – future commit summarization command module.

Planned features (vNext):
    • Read the last N commits and produce an LLM-generated paragraph summary.
    • Useful for quick PR descriptions or stand-ups.

Implementation will be wired into Typer in a later step.
"""


def summarize_commits(repo_path: str | None = None, n: int = 10) -> str:  # pragma: no cover
    """
    Placeholder helper.

    Parameters
    ----------
    repo_path
        Path to the Git repository (default = cwd).
    n
        Number of commits to include in the summary.

    Returns
    -------
    str
        Empty string for now. Real logic will call Groq to summarize.
    """
    return ""
