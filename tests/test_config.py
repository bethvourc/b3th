from pathlib import Path
import pytest

from b3th import config


# ------------------------------------------------------------------
# Autouse fixture: isolate env so real tokens don't leak into tests
# ------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("GITHUB_TOKEN", "GITHUB_PAT", "GROQ_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    # Also clear config path vars by default; individual tests can set them.
    for var in ("B3TH_CONFIG", "XDG_CONFIG_HOME"):
        monkeypatch.delenv(var, raising=False)


# ----------------------
# Original baseline tests
# ----------------------

def test_token_from_env(monkeypatch):
    """Env var should take priority over config file."""
    monkeypatch.setenv("GITHUB_TOKEN", "envtok")
    assert config.get_github_token() == "envtok"


def test_token_from_file(monkeypatch, tmp_path: Path):
    """Token is loaded from config file when env vars are missing."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('[github]\ntoken = "filetok"\n')
    monkeypatch.setenv("B3TH_CONFIG", str(cfg_file))
    assert config.get_github_token() == "filetok"


def test_token_missing(monkeypatch, tmp_path: Path):
    """Expect ConfigError when the token is nowhere to be found."""
    monkeypatch.setenv("B3TH_CONFIG", str(tmp_path / "nonexistent.toml"))
    with pytest.raises(config.ConfigError):
        config.get_github_token()


# ----------------------
# Additional coverage
# ----------------------

# GitHub token: more branches

def test_github_token_required_false_returns_none(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("B3TH_CONFIG", str(tmp_path / "nope.toml"))
    assert config.get_github_token(required=False) is None


def test_github_token_from_file_strips_whitespace(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('[github]\n token = "  filetok  " \n')
    monkeypatch.setenv("B3TH_CONFIG", str(cfg))
    assert config.get_github_token() == "filetok"


# Groq key: env, file, and missing

def test_groq_key_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "ENVKEY")
    assert config.get_groq_key() == "ENVKEY"


def test_groq_key_from_file(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('[groq]\napi_key = "from_file"\n')
    monkeypatch.setenv("B3TH_CONFIG", str(cfg))
    assert config.get_groq_key() == "from_file"


def test_groq_key_missing_required_false(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("B3TH_CONFIG", str(tmp_path / "missing.toml"))
    assert config.get_groq_key(required=False) is None


def test_groq_key_missing_raises(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("B3TH_CONFIG", str(tmp_path / "missing.toml"))
    with pytest.raises(config.ConfigError):
        config.get_groq_key(required=True)


# TOML loading & path resolution

def test_invalid_toml_is_ignored(monkeypatch, tmp_path: Path):
    """
    Ensure invalid TOML doesn't crash and returns {} → no token (with required=False).
    Explicitly clear env again for paranoia since config loaded a .env at import.
    """
    bad = tmp_path / "config.toml"
    bad.write_text("not = valid = toml")
    monkeypatch.setenv("B3TH_CONFIG", str(bad))
    # Double-ensure no env token leaks in
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_PAT", raising=False)

    assert config.get_github_token(required=False) is None


def test_toml_load_oserror_is_ignored(monkeypatch, tmp_path: Path):
    """Simulate tomllib.load raising OSError to hit that except path."""
    cfg = tmp_path / "config.toml"
    cfg.write_text('[github]\ntoken="t"\n')  # file exists to pass is_file()
    monkeypatch.setenv("B3TH_CONFIG", str(cfg))

    def boom(_fh):
        raise OSError("fs error")

    monkeypatch.setattr(config.tomllib, "load", boom, raising=True)
    # Double-ensure no env token leaks in
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_PAT", raising=False)

    # Loader returns {} on OSError → no token found (required=False)
    assert config.get_github_token(required=False) is None


def test__config_path_respects_override_and_xdg(monkeypatch, tmp_path: Path):
    # B3TH_CONFIG wins
    override = tmp_path / "ovr.toml"
    monkeypatch.setenv("B3TH_CONFIG", str(override))
    assert config._config_path() == override

    # Without override, XDG_CONFIG_HOME is used
    monkeypatch.delenv("B3TH_CONFIG", raising=False)
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    p = config._config_path()
    assert p == xdg / "b3th" / "config.toml"


def test__config_path_default_home_when_no_xdg(monkeypatch, tmp_path: Path):
    """Covers the default ~/.config path fallback when XDG is unset."""
    monkeypatch.delenv("B3TH_CONFIG", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    # Force Path.home() to our tmp dir
    monkeypatch.setattr(config.Path, "home", lambda: tmp_path, raising=False)
    assert config._config_path() == tmp_path / ".config" / "b3th" / "config.toml"


def test__from_toml_handles_non_mapping(monkeypatch):
    # Force _load_config to return a non-mapping; expect None
    monkeypatch.setattr(config, "_load_config", lambda: "oops", raising=True)
    assert config._from_toml("github", "token") is None


# require(): success & helpful error

def test_require_success_strips_and_returns_value():
    out = config.require("GitHub token", "  tok  ", "provide a token")
    assert out == "tok"


def test_require_raises_with_hint_and_path(monkeypatch, tmp_path: Path):
    custom = tmp_path / "cfg.toml"
    monkeypatch.setenv("B3TH_CONFIG", str(custom))
    with pytest.raises(config.ConfigError) as ex:
        config.require("GitHub token", None, "please set it")
    msg = str(ex.value)
    assert "GitHub token" in msg
    assert "please set it" in msg
    assert str(custom) in msg  # message should reference resolved config path
