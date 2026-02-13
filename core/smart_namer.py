from __future__ import annotations

import re
from pathlib import Path

from core.normalizer import is_filename_valid, sanitize_filename

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
LONG_RANDOM_RE = re.compile(r"\b(?=[A-Za-z0-9]{20,}\b)(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]+\b")


def detect_uuid_like(name: str) -> bool:
    stem = Path(name).stem
    return bool(UUID_RE.search(stem) or LONG_RANDOM_RE.search(stem))


def _extract_meaningful_tokens(stem: str) -> list[str]:
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", stem) if t]
    stop = {"pec", "email", "posta", "elettronica", "signed", "firmato", "pdf", "msg", "eml", "spa"}
    out = [t.upper() for t in tokens if t.lower() not in stop and len(t) >= 2]
    return out


def classify_filename(name: str) -> str | None:
    """Disabled semantic classification to preserve original wording strictly."""
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


def _signed_suffix(stem: str) -> str:
    low = stem.lower()
    has_signed = "_signed" in low or low.endswith("signed")
    has_firmato = "firmato" in low
    if has_signed:
        return "_signed"
    if has_firmato:
        return "_firmato"
    return ""


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

    label = sanitize_filename(stem, max_len=max_filename_len)
    suffix = _signed_suffix(stem)

    if suffix and label.lower().endswith(suffix):
        candidate_stem = label
    else:
        candidate_stem = f"{label}{suffix}"

    candidate = sanitize_filename(f"{candidate_stem}{extension}", max_len=max_filename_len)

    if output_dir and len(str(Path(output_dir) / candidate)) > max_output_path_len:
        base = Path(candidate).stem
        extn = Path(candidate).suffix
        while len(str(Path(output_dir) / candidate)) > max_output_path_len and len(base) > 12:
            base = base[:-1]
            candidate = f"{base}{extn}"
        if len(str(Path(output_dir) / candidate)) > max_output_path_len:
            candidate = sanitize_filename(candidate, max_len=max(20, max_filename_len - 10))
        reasons.append("path_too_long_mitigated")

    candidate = candidate.replace("_signed_signed", "_signed").replace("_firmato_firmato", "_firmato")
    return candidate, reasons
