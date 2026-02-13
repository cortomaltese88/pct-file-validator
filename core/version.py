from __future__ import annotations

import os
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as pkg_version

from core import __version__


def get_app_version() -> str:
    try:
        return pkg_version("gdlex-pct-validator")
    except PackageNotFoundError:
        return __version__


def get_build_info() -> str:
    commit = os.getenv("GIT_COMMIT") or os.getenv("GITHUB_SHA")
    build_date = os.getenv("BUILD_DATE") or os.getenv("GITHUB_RUN_STARTED_AT")

    if not build_date:
        build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if commit:
        return f"{commit[:8]} · {build_date}"
    return f"dev · {build_date}"
