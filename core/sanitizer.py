from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from core.fs_ops import create_backup, create_output_folder, sha256_file
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


def _sanitize_zip(src: Path, dst: Path, profile: dict) -> None:
    allowed = set(profile["allowed_formats"])
    warning = set(profile.get("warning_formats", []))
    used_names: set[str] = set()

    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.is_dir():
                continue
            raw_name = Path(info.filename).name
            if raw_name in {".DS_Store", "Thumbs.db"} or raw_name.startswith("~$"):
                continue

            ext = Path(raw_name).suffix.lower().lstrip(".")
            if ext not in allowed and ext not in warning:
                continue

            normalized = sanitize_filename(raw_name, max_len=int(profile.get("filename", {}).get("max_length", 80)))
            normalized = _safe_target_name(normalized, used_names)
            zout.writestr(normalized, zin.read(info.filename))


def sanitize(input_root: Path, profile: dict, dry_run: bool = False) -> tuple[Path | None, AnalysisSummary]:
    summary = analyze(input_root, profile)
    if dry_run:
        return None, summary

    source_root = input_root if input_root.is_dir() else input_root.parent
    output_dir = create_output_folder(source_root)
    create_backup(source_root, output_dir)

    sanitized_dir = output_dir / "sanitized"
    sanitized_dir.mkdir(exist_ok=True)

    used_names: set[str] = set()
    manifest: list[dict] = []

    for index, result in enumerate(summary.files, start=1):
        src = result.source
        prefixed = f"{index:02d}_{sanitize_filename(src.name, int(profile.get('filename', {}).get('max_length', 80)))}"
        target_name = _safe_target_name(prefixed, used_names)
        dst = sanitized_dir / target_name

        if src.suffix.lower() == ".zip":
            _sanitize_zip(src, dst, profile)
        else:
            shutil.copy2(src, dst)

        manifest.append(
            {
                "source": str(src),
                "target": str(dst),
                "sha256": sha256_file(dst),
                "status": result.status,
                "issues": [issue.__dict__ for issue in result.issues],
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
        "Esito analisi:",
    ]
    for item in summary.files:
        lines.append(f"- {item.source.name}: {item.status.upper()}")
        for issue in item.issues:
            lines.append(f"  [{issue.level.upper()}] {issue.code}: {issue.message}")

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
