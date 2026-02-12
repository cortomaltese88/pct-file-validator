from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_output_folder(source_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = source_root.parent / f"{source_root.name}_PDUA_OK_{timestamp}"
    output.mkdir(parents=True, exist_ok=False)
    return output


def create_backup(source_root: Path, destination: Path) -> Path:
    backup_dir = destination / "backup_originali"
    shutil.copytree(source_root, backup_dir)
    return backup_dir
