from __future__ import annotations

import csv
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from core.fs_ops import sha256_file
from core.models import AnalysisSummary, FileAnalysis, Issue
from core.normalizer import sanitize_filename
from core.reporting import build_technical_report
from core.smart_namer import ensure_unique, smart_rename
from core.validators import validate_path

OUTCOME_NOT_RUN = "NON ESEGUITA"
OUTCOME_OK = "OK"
OUTCOME_FIXED = "CORRETTA"
OUTCOME_PARTIAL = "PARZIALE"
OUTCOME_IMPOSSIBLE = "IMPOSSIBILE"
OUTCOME_ERROR = "ERRORE"

TECHNICAL_FILENAMES = {"report.json", "report.txt", "manifest.csv"}


def _is_ignored_path(path: Path) -> bool:
    lower_parts = [part.lower() for part in path.parts]
    if ".gdlex" in lower_parts:
        return True
    if any(part.endswith("_conforme") or part.endswith("_sanitized") for part in lower_parts):
        return True
    if path.name.lower() in TECHNICAL_FILENAMES:
        return True
    return False


def iter_input_files(input_root: Path) -> list[Path]:
    if input_root.is_file():
        return [] if _is_ignored_path(input_root) else [input_root]
    return [p for p in sorted(input_root.rglob("*")) if p.is_file() and not _is_ignored_path(p)]


def analyze(input_root: Path, profile: dict) -> AnalysisSummary:
    files = [validate_path(path, profile) for path in iter_input_files(input_root)]
    for item in files:
        item.correction_outcome = OUTCOME_NOT_RUN
    return AnalysisSummary(files=files)


def _safe_target_name(base_name: str, used: set[str]) -> str:
    return ensure_unique(used, base_name)


def resolve_output_dir(input_root: Path, output_mode: str = "sibling", custom_output_dir: Path | None = None) -> Path:
    if output_mode == "custom" and custom_output_dir:
        suffix_name = input_root.stem if input_root.is_file() else input_root.name
        return custom_output_dir / f"{suffix_name}_conforme"

    if input_root.is_dir():
        return input_root.parent / f"{input_root.name}_conforme"
    return input_root.parent / f"{input_root.stem}_conforme"


def _sanitize_zip(src: Path, dst: Path, profile: dict) -> tuple[list[str], bool]:
    """Restituisce (azioni, impossible)."""
    allowed = set(profile["allowed_formats"])
    warning = set(profile.get("warning_formats", []))
    max_len = int(profile.get("filename", {}).get("max_length", 80))

    actions: list[str] = ["[ZIP] Avvio riparazione archivio"]
    used_names: set[str] = set()
    impossible = False

    with tempfile.TemporaryDirectory(prefix="gdlex_zip_") as tempdir:
        temp_root = Path(tempdir)
        with zipfile.ZipFile(src, "r") as zin:
            zin.extractall(temp_root)

        pairs: list[tuple[str, bytes]] = []
        for file_path in sorted(p for p in temp_root.rglob("*") if p.is_file()):
            raw_name = file_path.name
            ext = file_path.suffix.lower().lstrip(".")

            if raw_name in {".DS_Store", "Thumbs.db"} or raw_name.startswith("~$"):
                actions.append(f"[ZIP] Rimosso file tecnico: {raw_name}")
                continue

            if ext not in allowed and ext not in warning:
                actions.append(f"[ZIP] Estensione interna vietata: {raw_name}")
                impossible = True
                continue

            normalized = sanitize_filename(raw_name, max_len=max_len)
            final_name = _safe_target_name(normalized, used_names)
            if final_name != raw_name:
                actions.append(f"[ZIP] Normalizzato: {raw_name} -> {final_name}")
            if file_path.parent != temp_root:
                actions.append(f"[ZIP] Flatten struttura: {file_path.relative_to(temp_root)}")

            pairs.append((final_name, file_path.read_bytes()))

        with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for name, blob in pairs:
                zout.writestr(name, blob)

    actions.append("[ZIP] Ricreato ZIP flat conforme")
    return actions, impossible


def _has_same_issue(target: FileAnalysis, code: str) -> bool:
    return any(issue.code == code for issue in target.issues)


def _build_manifest_row(result: FileAnalysis) -> dict:
    return {
        "source": str(result.source),
        "target": str(result.output_path) if result.output_path else None,
        "sha256": result.sha256,
        "status": result.status,
        "issues": [{"level": issue.level, "code": issue.code, "message": issue.message} for issue in result.issues],
        "correction_outcome": result.correction_outcome,
        "actions": result.correction_actions,
    }


def sanitize(
    input_root: Path,
    profile: dict,
    dry_run: bool = False,
    output_mode: str = "sibling",
    custom_output_dir: Path | None = None,
    smart_opts: dict | None = None,
    create_backup: bool = False,
) -> tuple[Path | None, AnalysisSummary]:
    summary = analyze(input_root, profile)
    if dry_run:
        return None, summary

    output_dir = resolve_output_dir(input_root, output_mode=output_mode, custom_output_dir=custom_output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tech_dir = output_dir / ".gdlex"
    tech_dir.mkdir(parents=True, exist_ok=True)

    if create_backup:
        backup_dir = tech_dir / "backup_originali"
        if input_root.is_dir():
            shutil.copytree(input_root, backup_dir, dirs_exist_ok=True)
        else:
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_root, backup_dir / input_root.name)

    used_targets: set[str] = set()
    smart_opts = smart_opts or {"enabled": True, "max_filename_len": 60, "max_output_path_len": 180}

    for result in summary.files:
        src = result.source
        max_len = int(profile.get("filename", {}).get("max_length", 80))
        merged_opts = {
            "enabled": smart_opts.get("enabled", True),
            "max_filename_len": int(smart_opts.get("max_filename_len", 60)),
            "max_output_path_len": int(smart_opts.get("max_output_path_len", 180)),
        }
        candidate, rename_reasons = smart_rename(src.name, src.suffix, merged_opts, {"output_dir": output_dir})
        if not candidate:
            candidate = sanitize_filename(src.name, max_len=max_len)
        target_name = _safe_target_name(candidate, used_targets)
        dst = output_dir / target_name

        try:
            ext = src.suffix.lower().lstrip(".")
            allowed = set(profile["allowed_formats"])
            warning = set(profile.get("warning_formats", []))

            if ext not in allowed and ext not in warning:
                result.correction_outcome = OUTCOME_IMPOSSIBLE
                result.correction_actions = ["Formato non ammesso: file escluso dalla correzione automatica"]
                continue

            actions: list[str] = []
            changed = False
            impossible = False
            if target_name != src.name:
                actions.append(f"Smart rename: {src.name} -> {target_name}")
                changed = True

            if ext == "zip":
                zip_actions, impossible = _sanitize_zip(src, dst, profile)
                actions.extend(zip_actions)
                changed = True
            else:
                shutil.copy2(src, dst)
                if dst.name != src.name:
                    actions.append(f"Rinominato file: {src.name} -> {dst.name}")
                else:
                    actions.append("Copia senza modifiche necessarie")

            reanalysis = validate_path(dst, profile)
            result.output_path = dst
            result.sha256 = sha256_file(dst)

            if _has_same_issue(reanalysis, "zip_ext_forbidden"):
                impossible = True
                actions.append("Persistono estensioni vietate nello ZIP: impossibile completare la correzione")

            if impossible:
                result.correction_outcome = OUTCOME_IMPOSSIBLE
            elif reanalysis.status == "ok" and changed:
                result.correction_outcome = OUTCOME_FIXED
            elif reanalysis.status == "ok" and not changed:
                result.correction_outcome = OUTCOME_OK
            elif changed:
                result.correction_outcome = OUTCOME_PARTIAL
            else:
                result.correction_outcome = OUTCOME_OK

            if _has_same_issue(reanalysis, "zip_mixed_pades"):
                actions.append("Warning mantenuto: mixed PAdES rilevato (non bloccante)")

            actions.append(f"Output scritto in: {dst}")
            result.correction_actions = actions
            result.status = reanalysis.status
            result.issues = list(reanalysis.issues)
            result.suggested_name = target_name

            if rename_reasons:
                result.issues.append(
                    Issue(
                        "info",
                        "smart_rename_applied",
                        f"Smart rename applicato: {src.name} -> {target_name} (motivi: {', '.join(rename_reasons)}).",
                    )
                )
            if "path_too_long_mitigated" in rename_reasons:
                result.issues.append(
                    Issue(
                        "warning",
                        "path_too_long_mitigated",
                        f"Path lungo mitigato per evitare problemi di sincronizzazione/cartelle annidate: {target_name}.",
                    )
                )

        except Exception as exc:  # pragma: no cover
            result.correction_outcome = OUTCOME_ERROR
            result.correction_actions = [f"Errore durante correzione: {exc}"]

    manifest_rows = [_build_manifest_row(item) for item in summary.files]

    report_json = tech_dir / "REPORT.json"
    report_txt = tech_dir / "REPORT.txt"
    manifest_csv = tech_dir / "MANIFEST.csv"

    with report_json.open("w", encoding="utf-8") as handle:
        json.dump({"output": str(output_dir), "files": manifest_rows}, handle, indent=2, ensure_ascii=False)

    _write_report_txt(report_txt, summary, output_dir)
    _write_manifest_csv(manifest_csv, summary)

    return output_dir, summary


def _write_manifest_csv(path: Path, summary: AnalysisSummary) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "output", "status", "correction_outcome", "sha256", "issues"])
        for item in summary.files:
            issues = "; ".join(f"{i.code}:{i.message}" for i in item.issues)
            writer.writerow(
                [
                    str(item.source),
                    str(item.output_path) if item.output_path else "",
                    item.status,
                    item.correction_outcome,
                    item.sha256 or "",
                    issues,
                ]
            )


def _write_report_txt(path: Path, summary: AnalysisSummary, output_dir: Path) -> None:
    header = [
        "GD LEX - REPORT CORREZIONE AUTOMATICA",
        "=" * 60,
        f"Output depositabile: {output_dir}",
        f"Report tecnico: {path.parent}",
        "",
    ]
    body = build_technical_report(summary)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(header) + body)
