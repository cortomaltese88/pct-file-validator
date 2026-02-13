import pytest

from core.version import get_app_version, get_build_info


def test_version_available():
    assert get_app_version()


def test_build_info_has_fallback():
    assert get_build_info()


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
