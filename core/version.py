from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version as pkg_version

PRIMARY_PACKAGE = "gdlex-pct-validator"
LEGACY_PACKAGE = "pct-file-validator"


def _from_tag_ref(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw[1:] if raw.startswith("v") else raw


def _git_tag_version() -> str | None:
    try:
        tag = (
            subprocess.check_output(["git", "describe", "--tags", "--exact-match"], stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .strip()
        )
        return _from_tag_ref(tag)
    except Exception:
        return None


def _version_from_metadata() -> str | None:
    for package in (PRIMARY_PACKAGE, LEGACY_PACKAGE):
        try:
            return pkg_version(package)
        except PackageNotFoundError:
            continue
    return None


def _version_from_pyproject() -> str | None:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject.exists():
        return None
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def get_app_version() -> str:
    # Prefer the actually installed package version shown to end-users.
    return (
        _version_from_metadata()
        or _version_from_pyproject()
        or _from_tag_ref(os.getenv("APP_VERSION"))
        or _from_tag_ref(os.getenv("GITHUB_REF_NAME"))
        or _from_tag_ref(os.getenv("GIT_TAG"))
        or _git_tag_version()
        or "dev"
    )


def get_build_info() -> str:
    commit = os.getenv("GIT_COMMIT") or os.getenv("GITHUB_SHA")
    build_date = os.getenv("BUILD_DATE") or os.getenv("GITHUB_RUN_STARTED_AT")
    if not build_date:
        build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{commit[:8]} · {build_date}" if commit else f"dev · {build_date}"
