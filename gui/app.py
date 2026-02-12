from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def _build_dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#eaeaea"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#232323"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1b1b1b"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#eaeaea"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#2a2a2a"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#eaeaea"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3daee9"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0b0b0b"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#8a8a8a"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#8a8a8a"))
    return palette


def main() -> int:
    QGuiApplication.setDesktopFileName("gdlex-pct-validator.desktop")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_build_dark_palette())
    app.setApplicationName("GD LEX – Verifica Deposito PCT/PDUA")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
