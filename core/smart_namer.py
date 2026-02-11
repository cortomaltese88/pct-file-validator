from __future__ import annotations

import re
from pathlib import Path

from core.normalizer import is_filename_valid, sanitize_filename

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
LONG_RANDOM_RE = re.compile(r"\b(?=[A-Za-z0-9]{20,}\b)(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]+\b")


def detect_uuid_like(name: str) -> bool:
    stem = Path(name).stem
    return bool(UUID_RE.search(stem) or LONG_RANDOM_RE.search(stem))


def classify_filename(name: str) -> str | None:
    lower = Path(name).stem.lower().replace("-", " ").replace("_", " ")
    if "pagopa" in lower or "ricevuta" in lower:
        return "Ricevuta_PagoPA"
    if "contributo" in lower and "unificat" in lower:
        return "Contributo_Unificato"
    if "precetto" in lower:
        return "Atto_Precetto"
    if "titolo" in lower and "esecutiv" in lower:
        return "Titolo_Esecutivo"
    if "decreto" in lower and "esecutor" in lower:
        return "Decreto_Esecutorieta"
    if "attestazione" in lower and "conform" in lower:
        return "Attestazione_Conformita"
    if "notifica" in lower or "ufficiale giudiziario" in lower:
        return "Notifica_Ufficiale_Giudiziario"
    if "pec" in lower or "email" in lower or "posta elettronica" in lower:
        return "PEC"
    return None


def ensure_unique(nameset: set[str], candidate: str) -> str:
    if candidate not in nameset:
        nameset.add(candidate)
        return candidate
    stem = Path(candidate).stem
    ext = Path(candidate).suffix
    idx = 2
    while True:
        alt = f"{stem}_{idx:02d}{ext}"
        if alt not in nameset:
            nameset.add(alt)
            return alt
        idx += 1


def smart_rename(name: str, ext: str, opts: dict, context: dict | None = None) -> tuple[str, list[str]]:
    enabled = bool(opts.get("enabled", True))
    max_filename_len = int(opts.get("max_filename_len", 60))
    max_output_path_len = int(opts.get("max_output_path_len", 180))

    original = Path(name).name
    stem = Path(original).stem
    extension = ext or Path(original).suffix
    if not extension.startswith("."):
        extension = f".{extension}" if extension else ""

    uuid_like = detect_uuid_like(stem)
    too_long = len(original) > max_filename_len
    invalid_name = not is_filename_valid(original, max_len=max_filename_len)

    output_dir = context.get("output_dir") if context else None
    path_too_long = bool(output_dir and len(str(Path(output_dir) / original)) > max_output_path_len)

    if not enabled:
        return sanitize_filename(original, max_len=max_filename_len), []

    reasons: list[str] = []
    if too_long:
        reasons.append("filename_too_long")
    if uuid_like:
        reasons.append("uuid_or_random_pattern")
    if path_too_long:
        reasons.append("path_too_long")
    if invalid_name:
        reasons.append("filename_invalid_chars")

    if not reasons:
        return original, []

    label = classify_filename(original) or sanitize_filename(stem, max_len=max_filename_len)

    signed_suffix = ""
    low_stem = stem.lower()
    if "_signed" in low_stem or " signed" in low_stem:
        signed_suffix = "_signed"
    elif "firmato" in low_stem:
        signed_suffix = "_firmato"

    candidate = sanitize_filename(f"{label}{signed_suffix}{extension}", max_len=max_filename_len)

    if output_dir and len(str(Path(output_dir) / candidate)) > max_output_path_len:
        base = Path(candidate).stem
        extn = Path(candidate).suffix
        while len(str(Path(output_dir) / candidate)) > max_output_path_len and len(base) > 12:
            base = base[:-1]
            candidate = f"{base}{extn}"
        if len(str(Path(output_dir) / candidate)) > max_output_path_len:
            candidate = sanitize_filename(candidate, max_len=max(20, max_filename_len - 10))
        reasons.append("path_too_long_mitigated")

    return candidate, reasons
