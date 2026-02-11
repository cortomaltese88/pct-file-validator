from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from core.fs_ops import sha256_file
from core.models import AnalysisSummary
from core.normalizer import sanitize_filename
from core.validators import validate_path


def iter_input_files(input_root: Path) -> list[Path]:
    if input_root.is_file():
        return [input_root]
    return [p for p in sorted(input_root.rglob("*")) if p.is_file()]


def analyze(input_root: Path, profile: dict) -> AnalysisSummary:
    files = [validate_path(path, profile) for path in iter_input_files(input_root)]
    return AnalysisSummary(files=files)


def _safe_target_name(base_name: str, used: set[str]) -> str:
    if base_name not in used:
        used.add(base_name)
        return base_name
    stem = Path(base_name).stem
    ext = Path(base_name).suffix
    index = 2
    while True:
        candidate = f"{stem}_{index:02d}{ext}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def _output_folder_for(input_root: Path) -> Path:
    if input_root.is_dir():
        return input_root.parent / f"{input_root.name}_conforme"
    return input_root.parent / f"{input_root.stem}_conforme"


def _sanitize_zip(src: Path, dst: Path, profile: dict) -> list[str]:
    allowed = set(profile["allowed_formats"])
    warning = set(profile.get("warning_formats", []))
    max_len = int(profile.get("filename", {}).get("max_length", 80))
    used_names: set[str] = set()
    actions: list[str] = ["Estratta struttura annidata"]

    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.is_dir():
                continue

            raw_name = info.filename
            base_name = Path(raw_name).name

            if raw_name != base_name:
                actions.append(f"Rimossa cartella annidata: {raw_name}")

            if base_name in {".DS_Store", "Thumbs.db"} or base_name.startswith("~$"):
                actions.append(f"Rimosso file vietato: {base_name}")
                continue

            ext = Path(base_name).suffix.lower().lstrip(".")
            if ext not in allowed and ext not in warning:
                actions.append(f"Rimosso file con estensione vietata: {base_name}")
                continue

            normalized = sanitize_filename(base_name, max_len=max_len)
            if normalized != base_name:
                actions.append(f"Normalizzato nome interno: {base_name} -> {normalized}")

            normalized = _safe_target_name(normalized, used_names)
            zout.writestr(normalized, zin.read(info.filename))

    actions.append("Ricreato ZIP flat conforme")
    return actions


def sanitize(input_root: Path, profile: dict, dry_run: bool = False) -> tuple[Path | None, AnalysisSummary]:
    summary = analyze(input_root, profile)
    if dry_run:
        return None, summary

    output_dir = _output_folder_for(input_root)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    manifest: list[dict] = []

    for index, result in enumerate(summary.files, start=1):
        src = result.source
        max_len = int(profile.get("filename", {}).get("max_length", 80))
        prefixed = f"{index:02d}_{sanitize_filename(src.name, max_len)}"
        target_name = _safe_target_name(prefixed, used_names)
        dst = output_dir / target_name

        ext = src.suffix.lower().lstrip(".")
        allowed = set(profile["allowed_formats"])
        warning = set(profile.get("warning_formats", []))

        actions: list[str] = []
        corrected = False
        partially = False

        if ext not in allowed and ext not in warning:
            result.correction_outcome = "✖ Non correggibile"
            result.correction_actions = ["Formato non ammesso: escluso dall'output"]
            manifest.append(
                {
                    "source": str(src),
                    "target": None,
                    "sha256": None,
                    "status": result.status,
                    "issues": [issue.__dict__ for issue in result.issues],
                    "correction_outcome": result.correction_outcome,
                    "actions": result.correction_actions,
                }
            )
            continue

        if src.suffix.lower() == ".zip":
            actions = _sanitize_zip(src, dst, profile)
            if any("Rimosso" in a for a in actions):
                partially = True
            corrected = True
        else:
            shutil.copy2(src, dst)
            if dst.name != src.name:
                actions.append(f"Rinominato: {src.name} -> {dst.name}")
                corrected = True
            else:
                actions.append("Copiato senza modifiche")

        if corrected and partially:
            result.correction_outcome = "⚠ Parzialmente corretto"
        elif corrected:
            result.correction_outcome = "✔ Corretto"
        else:
            result.correction_outcome = "✖ Non correggibile"
        result.correction_actions = actions

        manifest.append(
            {
                "source": str(src),
                "target": str(dst),
                "sha256": sha256_file(dst),
                "status": result.status,
                "issues": [issue.__dict__ for issue in result.issues],
                "correction_outcome": result.correction_outcome,
                "actions": actions,
            }
        )

    manifest_path = output_dir / "manifest.json"
    report_path = output_dir / "report.txt"

    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump({"files": manifest}, handle, indent=2, ensure_ascii=False)

    _write_report(report_path, summary, output_dir)
    return output_dir, summary


def _write_report(report_path: Path, summary: AnalysisSummary, output_dir: Path) -> None:
    lines = [
        "GD LEX - Report tecnico e giuridico-informatico",
        "=" * 60,
        f"Output: {output_dir}",
        "",
        "Esito analisi e correzioni:",
    ]
    for item in summary.files:
        lines.append(f"- {item.source.name}: {item.status.upper()} | {item.correction_outcome or 'N/D'}")
        for issue in item.issues:
            lines.append(f"  [{issue.level.upper()}] {issue.code}: {issue.message}")
        for action in item.correction_actions:
            lines.append(f"  - {action}")

    lines.extend(
        [
            "",
            "Avvertenze legali:",
            "Il tool applica controlli conservativi e non sostituisce la verifica professionale del difensore.",
            "Conservare il presente report insieme alla documentazione di deposito.",
        ]
    )

    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
