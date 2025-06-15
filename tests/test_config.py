from pathlib import Path

import pytest

from b3th import config


def test_token_from_env(monkeypatch):
    """Env var should take priority over config file."""
    monkeypatch.setenv("GITHUB_TOKEN", "envtok")
    assert config.get_github_token() == "envtok"


def test_token_from_file(monkeypatch, tmp_path: Path):
    """Token is loaded from config file when env vars are missing."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('[github]\ntoken = "filetok"\n')

    # Ensure env vars are absent
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_PAT", raising=False)

    # Point b3th at the temporary config
    monkeypatch.setenv("B3TH_CONFIG", str(cfg_file))

    assert config.get_github_token() == "filetok"


def test_token_missing(monkeypatch, tmp_path: Path):
    """Expect ConfigError when the token is nowhere to be found."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_PAT", raising=False)
    monkeypatch.setenv("B3TH_CONFIG", str(tmp_path / "nonexistent.toml"))

    with pytest.raises(config.ConfigError):
        config.get_github_token()
