__version__: str = "0.1.0"

# Surface key helpers at package level

from .commit_message import generate_commit_message  # noqa: F401

__all__ = ["__version__", "generate_commit_message"]
