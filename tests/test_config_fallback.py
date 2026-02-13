import json
from pathlib import Path

import pytest

import core.config as cfg


def test_load_config_prefers_custom_path(tmp_path: Path):
    custom = tmp_path / "custom.yaml"
    custom.write_text(json.dumps({"profiles": {"pdua_safe": {"allowed_formats": ["pdf"]}}}), encoding="utf-8")

    data = cfg.load_config(custom)
    assert "profiles" in data
    assert "pdua_safe" in data["profiles"]


def test_load_config_raises_when_custom_missing(tmp_path: Path):
    missing = tmp_path / "missing.yaml"
    with pytest.raises(cfg.ConfigError):
        cfg.load_config(missing)


def test_load_config_creates_user_fallback(tmp_path: Path, monkeypatch):
    user_dir = tmp_path / "home"
    monkeypatch.setenv("APPDATA", str(user_dir))

    out = user_dir / "GDLEX-PCT-Validator" / "default.yaml"
    assert not out.exists()

    monkeypatch.setattr(cfg, "DEFAULT_CONFIG_PATH", tmp_path / "missing-default.yaml")

    data = cfg.load_config()
    assert out.exists()
    assert "profiles" in data
