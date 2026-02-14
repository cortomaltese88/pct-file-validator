import pytest

import core.version as version_module
from core.version import get_app_version, get_build_info, get_version_info


def test_version_available():
    assert get_app_version()


def test_build_info_has_fallback():
    assert get_build_info()


def test_build_info_module_has_priority_over_metadata(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "")
    monkeypatch.setattr(version_module, "_build_info_values", lambda: ("1.1.11", "2026-02-13", "deb"))
    monkeypatch.setattr(version_module, "_version_from_metadata", lambda: "1.0.0")
    assert get_app_version() == "1.1.11"


def test_env_app_version_has_priority(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.1.12")
    monkeypatch.setattr(version_module, "_build_info_values", lambda: ("1.1.11", "2026-02-13", "deb"))
    assert get_app_version() == "1.1.12"


def test_build_info_output_avoids_dev_with_packaged_build(monkeypatch):
    monkeypatch.setattr(version_module, "_build_info_values", lambda: ("1.1.11", "2026-02-13", "windows"))
    build = get_build_info()
    assert "dev" not in build.lower()
    assert "2026-02-13" in build


def test_version_info_never_uses_hardcoded_1_0_0(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setattr(version_module, "_build_info_values", lambda: ("1.1.11", "2026-02-13", "deb"))
    monkeypatch.setattr(version_module, "_version_from_metadata", lambda: None)
    monkeypatch.setattr(version_module, "_version_from_pyproject", lambda: None)
    monkeypatch.setattr(version_module, "_git_tag_version", lambda: None)

    info = get_version_info()
    assert info["version"] == "1.1.11"
    assert info["version"] != "1.0.0"


def test_main_window_title_contains_version():
    pytest.importorskip("PySide6", exc_type=ImportError)
    qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    QApplication = qtwidgets.QApplication
    from gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert get_app_version() in window.windowTitle()
    window.close()
    app.quit()
