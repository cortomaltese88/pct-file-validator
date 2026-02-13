from pathlib import Path

from core import config as cfg


def test_load_config_falls_back_to_user_config(tmp_path: Path, monkeypatch):
    missing_default = tmp_path / "missing" / "default.yaml"
    user_dir = tmp_path / "appdata"

    monkeypatch.setattr(cfg, "DEFAULT_CONFIG_PATH", missing_default)
    monkeypatch.setenv("APPDATA", str(user_dir))

    data = cfg.load_config()
    out = user_dir / "GDLEX-PCT-Validator" / "default.yaml"
    assert out.exists()
    assert "profiles" in data
    assert "pdua_safe" in data["profiles"]


def test_load_config_explicit_missing_still_raises(tmp_path: Path):
    missing = tmp_path / "missing.yaml"
    try:
        cfg.load_config(missing)
        assert False, "Expected ConfigError"
    except cfg.ConfigError:
        pass
