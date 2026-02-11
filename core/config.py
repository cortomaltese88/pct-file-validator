from __future__ import annotations

import json
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


class ConfigError(RuntimeError):
    """Errore di configurazione."""


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "default.yaml"


def load_config(config_path: Path | None = None) -> dict:
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        raise ConfigError(f"Configurazione non trovata: {path}")

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
