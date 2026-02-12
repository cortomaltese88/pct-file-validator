from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version as pkg_version

from core import __version__


def get_app_version() -> str:
    try:
        return pkg_version("gdlex-pct-validator")
    except PackageNotFoundError:
        return __version__


def get_build_info() -> str:
    commit = os.getenv("GIT_COMMIT") or os.getenv("GITHUB_SHA")
    if commit:
        return commit[:8]
    return "local"
