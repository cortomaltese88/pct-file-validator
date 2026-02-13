from __future__ import annotations

import os
import re
import subprocess
from importlib import import_module
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

PRIMARY_PACKAGE = "gdlex-pct-validator"
LEGACY_PACKAGE = "pct-file-validator"
UNKNOWN_VERSION = "0.0.0+unknown"


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


def _build_info_values() -> tuple[str | None, str | None, str | None]:
    try:
        module = import_module("core._build_info")
    except Exception:
        return None, None, None

    version = getattr(module, "__version__", None)
    build = getattr(module, "__build__", None)
    channel = getattr(module, "__channel__", None)

    if version in {None, "", UNKNOWN_VERSION}:
        version = None
    if build in {None, "", "unknown"}:
        build = None
    if channel in {None, "", "unknown"}:
        channel = None

    return version, build, channel


def get_app_version() -> str:
    env_version = _from_tag_ref(os.getenv("APP_VERSION"))
    build_version, _, _ = _build_info_values()

    return (
        env_version
        or build_version
        or _version_from_metadata()
        or _from_tag_ref(os.getenv("GITHUB_REF_NAME"))
        or _from_tag_ref(os.getenv("GIT_TAG"))
        or _git_tag_version()
        or _version_from_pyproject()
        or UNKNOWN_VERSION
    )


def get_build_info() -> str:
    _, build_date, build_channel = _build_info_values()
    commit = os.getenv("GIT_COMMIT") or os.getenv("GITHUB_SHA")

    if commit:
        date = os.getenv("BUILD_DATE") or os.getenv("GITHUB_RUN_STARTED_AT") or build_date
        return f"{commit[:8]} · {date}" if date else commit[:8]

    if build_date and build_channel:
        return f"{build_date} · {build_channel}"
    if build_date:
        return build_date

    dynamic_date = os.getenv("BUILD_DATE") or os.getenv("GITHUB_RUN_STARTED_AT")
    if dynamic_date:
        return dynamic_date

    return "unknown"


def get_version_info() -> dict[str, str]:
    return {
        "version": get_app_version(),
        "build": get_build_info(),
    }
