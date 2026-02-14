from __future__ import annotations

import io
import zipfile
from pathlib import Path

from core.models import FileAnalysis, Issue
from core.normalizer import is_filename_valid, sanitize_filename

MACOS_JUNK = {"__MACOSX", ".DS_Store", "Thumbs.db"}


def file_type(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def detect_status(issues: list[Issue]) -> str:
    if any(i.level == "error" for i in issues):
        return "error"
    if any(i.level == "warning" for i in issues):
        return "warning"
    return "ok"


def validate_pdf(path: Path) -> list[Issue]:
    issues: list[Issue] = []
    blob = path.read_bytes()
    if not blob.startswith(b"%PDF"):
        issues.append(Issue("error", "pdf_header", "Header PDF non valido."))
        return issues

    if b"%%EOF" not in blob[-2048:]:
        issues.append(Issue("error", "pdf_integrity", "Trailer EOF PDF non trovato; file potenzialmente corrotto."))

    if b"/Encrypt" in blob:
        issues.append(Issue("error", "pdf_encrypted", "PDF cifrato/non apribile senza password."))

    if b"/ByteRange" in blob and b"/Contents" in blob:
        issues.append(Issue("info", "pades_detected", "Possibile firma PAdES rilevata."))

    return issues


def _validate_zip_entries(names: list[str], allowed_exts: set[str], warning_exts: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    has_pades = False
    has_unsigned_pdf = False

    for name in names:
        if any(name.startswith(f"{junk}/") or name == junk for junk in MACOS_JUNK):
            issues.append(Issue("error", "zip_junk", f"Elemento non ammesso nello ZIP: {name}"))
            continue
        if name.startswith("~$"):
            issues.append(Issue("error", "zip_temp", f"File temporaneo non ammesso: {name}"))
            continue
        if "/" in name.strip("/"):
            issues.append(Issue("error", "zip_nested", f"ZIP non flat (contiene cartelle): {name}"))
        base = Path(name).name
        if base.count(".") > 1:
            issues.append(Issue("error", "zip_double_ext", f"Doppia estensione: {base}"))

        ext = Path(base).suffix.lower().lstrip(".")
        if ext in warning_exts:
            issues.append(Issue("warning", "zip_warning_ext", f"Formato nello ZIP ammesso con warning: {base}"))
        elif ext not in allowed_exts:
            issues.append(Issue("error", "zip_ext_forbidden", f"Formato non ammesso nello ZIP: {base}"))

        if not is_filename_valid(base):
            issues.append(Issue("warning", "zip_name", f"Nome nello ZIP da normalizzare: {base}"))

        if ext == "pdf" and "signed" in base.lower():
            has_pades = True
        if ext == "pdf" and "signed" not in base.lower():
            has_unsigned_pdf = True

    if has_pades and has_unsigned_pdf:
        issues.append(Issue("warning", "zip_mixed_pades", "PDF firmati e non firmati nello stesso ZIP."))
    return issues


def validate_zip(path: Path, allowed_exts: set[str], warning_exts: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            issues.extend(_validate_zip_entries(names, allowed_exts, warning_exts))
    except zipfile.BadZipFile:
        issues.append(Issue("error", "zip_corrupt", "Archivio ZIP corrotto."))
    return issues


def validate_path(path: Path, profile: dict) -> FileAnalysis:
    allowed = set(profile["allowed_formats"])
    warnings = set(profile.get("warning_formats", []))
    max_len = int(profile.get("filename", {}).get("max_length", 80))

    issues: list[Issue] = []
    base = path.name
    ext = file_type(path)

    if ext in warnings:
        issues.append(Issue("warning", "ext_warning", f"Formato '{ext}' ammesso con cautela."))
    elif ext not in allowed:
        issues.append(Issue("error", "ext_forbidden", f"Formato '{ext}' non ammesso dal profilo."))

    if not is_filename_valid(base, max_len=max_len):
        issues.append(Issue("warning", "filename_normalize", "Nome file da normalizzare."))

    if ext == "pdf":
        issues.extend(validate_pdf(path))
    elif ext == "zip":
        issues.extend(validate_zip(path, allowed, warnings))

    status = detect_status(issues)
    return FileAnalysis(
        source=path,
        file_type=ext or "unknown",
        status=status,
        issues=issues,
        suggested_name=sanitize_filename(base, max_len=max_len),
    )


def detect_pdf_signature(raw_bytes: bytes) -> bool:
    return b"/ByteRange" in raw_bytes and b"/Contents" in raw_bytes


def zip_bytes_from_pairs(files: list[tuple[str, bytes]]) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, blob in files:
            zf.writestr(name, blob)
    return data.getvalue()
