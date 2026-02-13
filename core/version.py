from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as pkg_version

PACKAGE_NAME = "gdlex-pct-validator"


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


def get_app_version() -> str:
    return (
        _from_tag_ref(os.getenv("APP_VERSION"))
        or _from_tag_ref(os.getenv("GITHUB_REF_NAME"))
        or _from_tag_ref(os.getenv("GIT_TAG"))
        or _git_tag_version()
        or _pkg_version_fallback()
    )


def _pkg_version_fallback() -> str:
    try:
        return pkg_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "dev"


def get_build_info() -> str:
    commit = os.getenv("GIT_COMMIT") or os.getenv("GITHUB_SHA")
    build_date = os.getenv("BUILD_DATE") or os.getenv("GITHUB_RUN_STARTED_AT")
    if not build_date:
        build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{commit[:8]} · {build_date}" if commit else f"dev · {build_date}"
