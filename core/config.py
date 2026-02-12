from __future__ import annotations

import json
import os
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


class ConfigError(RuntimeError):
    """Errore di configurazione."""


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "default.yaml"

FALLBACK_CONFIG: dict = {
    "profiles": {
        "standard": {
            "allowed_formats": ["pdf", "p7m", "zip", "rtf", "txt", "xml", "html", "jpg", "jpeg", "eml", "msg"],
            "warning_formats": ["png", "gif", "tiff", "mp3", "mp4", "wav", "avi", "mov"],
            "filename": {"max_length": 80},
        },
        "pdua_safe": {
            "allowed_formats": ["pdf", "p7m", "zip", "rtf", "txt", "xml", "html", "jpg", "jpeg", "eml", "msg"],
            "warning_formats": ["png", "gif", "tiff", "mp3", "mp4", "wav", "avi", "mov"],
            "filename": {"max_length": 80},
        },
        "pduasuper": {
            "allowed_formats": ["pdf", "p7m", "zip", "rtf", "txt", "xml", "html", "jpg", "jpeg", "eml", "msg"],
            "warning_formats": ["png", "gif", "tiff", "mp3", "mp4", "wav", "avi", "mov"],
            "filename": {"max_length": 70},
        },
    }
}


def _user_default_config_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "GDLEX-PCT-Validator" / "default.yaml"
    return Path.home() / ".config" / "GDLEX-PCT-Validator" / "default.yaml"


def _write_fallback_user_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(FALLBACK_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")


def load_config(config_path: Path | None = None) -> dict:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        if config_path is not None:
            raise ConfigError(f"Configurazione non trovata: {path}")
        user_cfg = _user_default_config_path()
        if not user_cfg.exists():
            _write_fallback_user_config(user_cfg)
        path = user_cfg

    raw = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(raw) or {}
    else:
        # fallback: default.yaml è scritto in YAML compatibile JSON
        data = json.loads(raw)

    if "profiles" not in data:
        raise ConfigError("Configurazione non valida: manca 'profiles'.")
    return data


def resolve_profile(config: dict, profile_name: str) -> dict:
    try:
        return config["profiles"][profile_name]
    except KeyError as exc:
        available = ", ".join(sorted(config.get("profiles", {}).keys()))
        raise ConfigError(f"Profilo '{profile_name}' non trovato. Disponibili: {available}") from exc
