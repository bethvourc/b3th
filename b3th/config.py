# b3th/config.py
"""
Configuration helpers for b3th.

Credential precedence (highest → lowest):
1) Real environment variables (including values loaded from a .env in the user's project)
2) TOML file: ~/.config/b3th/config.toml (or $XDG_CONFIG_HOME/b3th/config.toml)
   - Overridable via B3TH_CONFIG=/path/to/config.toml

Supports:
- GitHub token via env: GITHUB_TOKEN or GITHUB_PAT, or in TOML under [github].token
- Groq API key via env: GROQ_API_KEY, or in TOML under [groq].api_key
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv

# Load a user's .env once, searching from the current working directory upward.
# We don't override real env vars by default.
load_dotenv(find_dotenv(usecwd=True), override=False)

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[assignment]


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


def _from_toml(section: str, key: str) -> str | None:
    """Fetch a string value from the TOML config at [section].key."""
    cfg = _load_config()
    if not isinstance(cfg, Mapping):
        return None
    sec = cfg.get(section)
    if isinstance(sec, Mapping):
        val = sec.get(key)
        return str(val).strip() if val is not None else None
    return None


def require(var_name: str, value: str | None, hint: str) -> str:
    """Return value if present; else raise a friendly ConfigError."""
    if value and value.strip():
        return value.strip()
    raise ConfigError(
        f"Missing {var_name}. {hint}\n"
        "Supply it via environment or a .env file in your project, "
        f"or via TOML at {_config_path()}."
    )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def get_github_token(required: bool = True) -> str | None:
    """
    Retrieve the GitHub personal-access token.

    Sources (in order): env GITHUB_TOKEN/GITHUB_PAT → TOML [github].token

    Parameters
    ----------
    required : bool
        If True, raise ConfigError when not found. If False, return None.

    Returns
    -------
    str | None
        The token, or None if not found and required=False.
    """
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    if not token:
        token = _from_toml("github", "token")

    if token:
        return token.strip()

    if required:
        raise ConfigError(
            "GitHub token not found. Set GITHUB_TOKEN (or GITHUB_PAT) in your "
            ".env/environment, or add it under [github].token in "
            f"{_config_path()}."
        )
    return None


def get_groq_key(required: bool = True) -> str | None:
    """
    Retrieve the Groq API key.

    Sources (in order): env GROQ_API_KEY → TOML [groq].api_key

    Parameters
    ----------
    required : bool
        If True, raise ConfigError when not found. If False, return None.

    Returns
    -------
    str | None
        The API key, or None if not found and required=False.
    """
    key = os.getenv("GROQ_API_KEY")
    if not key:
        key = _from_toml("groq", "api_key")

    if key:
        return key.strip()

    if required:
        raise ConfigError(
            "Groq API key not found. Set GROQ_API_KEY in your .env/environment, "
            "or add it under [groq].api_key in "
            f"{_config_path()}."
        )
    return None
