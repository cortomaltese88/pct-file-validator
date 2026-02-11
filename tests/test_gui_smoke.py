import pytest


def test_main_window_constructs():
    pytest.importorskip("PySide6", exc_type=ImportError)
    qtwidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    QApplication = qtwidgets.QApplication

    from gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle()
    window.close()
    app.quit()
