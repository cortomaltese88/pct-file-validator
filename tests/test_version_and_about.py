import pytest

import core.version as version_module
from core.version import get_app_version, get_build_info


def test_version_available():
    assert get_app_version()


def test_build_info_has_fallback():
    assert get_build_info()


def test_installed_metadata_version_has_priority(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    monkeypatch.setattr(version_module, "_version_from_metadata", lambda: "1.1.10")
    monkeypatch.setattr(version_module, "_version_from_pyproject", lambda: None)
    assert get_app_version() == "1.1.10"


def test_legacy_package_fallback(monkeypatch):
    monkeypatch.setattr(version_module, "_version_from_metadata", lambda: "1.1.9")
    monkeypatch.setattr(version_module, "_version_from_pyproject", lambda: None)
    assert get_app_version() == "1.1.9"


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
