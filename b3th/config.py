"""
Configuration helpers for b3th.

Currently supports retrieving a GitHub token from (highest-to-lowest priority):

1. Environment variables: ``GITHUB_TOKEN`` or ``GITHUB_PAT``.
2. A TOML file (default: ``~/.config/b3th/config.toml`` or
   ``$XDG_CONFIG_HOME/b3th/config.toml``).
   You can also override the path with ``B3TH_CONFIG``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # back-port package for <3.11


class ConfigError(RuntimeError):
    """Raised when a required configuration value is missing."""


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _config_path() -> Path:
    """Return the filesystem path to the main config file."""
    # Explicit override wins
    if env_path := os.getenv("B3TH_CONFIG"):
        return Path(env_path).expanduser()

    # Respect XDG if set, else fallback to ~/.config
    base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "b3th" / "config.toml"


def _load_config() -> Mapping[str, Any]:
    """Load the TOML config if it exists; otherwise return an empty mapping."""
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (tomllib.TOMLDecodeError, OSError):
        return {}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def get_github_token() -> str:
    """
    Retrieve the GitHub personal-access token.

    Raises
    ------
    ConfigError
        If the token is not found in env vars or the config file.
    """
    # 1. Environment variables
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    if token:
        return token.strip()

    # 2. Config file
    cfg = _load_config()
    token = (
        cfg.get("github", {}).get("token")  # type: ignore[arg-type]
        if isinstance(cfg, Mapping)
        else None
    )
    if token:
        return str(token).strip()

    # Nothing found
    raise ConfigError(
        "GitHub token not found. Set GITHUB_TOKEN (or GITHUB_PAT) "
        "or add it under [github] in ~/.config/b3th/config.toml."
    )
