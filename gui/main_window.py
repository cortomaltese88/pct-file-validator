from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config import load_config, resolve_profile
from core.sanitizer import analyze, sanitize


class DropArea(QFrame):
    def __init__(self, on_path_dropped):
        super().__init__()
        self.on_path_dropped = on_path_dropped
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame { border: 2px dashed #6b7280; border-radius: 6px; background: #f8fafc; }")
        layout = QVBoxLayout(self)
        label = QLabel("Trascina qui file o cartella")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        self.on_path_dropped(path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GD LEX – Verifica Deposito PCT/PDUA")
        self.resize(1100, 760)
        self.input_path: Path | None = None
        self.last_output: Path | None = None

        self.config = load_config()
        self.profile = resolve_profile(self.config, "pdua_safe")

        self._setup_palette()
        self._build_ui()

    def _setup_palette(self) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f1f5f9"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#0f172a"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        self.setPalette(palette)

    def _build_ui(self) -> None:
        container = QWidget()
        root = QVBoxLayout(container)

        self.drop_area = DropArea(self._set_input_path)
        root.addWidget(self.drop_area)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Originale", "Tipo", "Stato", "Problemi", "Nuovo Nome", "Azioni"])
        root.addWidget(self.table)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Dettagli tecnici selezione file")
        root.addWidget(self.details)

        button_row = QHBoxLayout()
        self.btn_analyze = QPushButton("Analizza")
        self.btn_sanitize = QPushButton("Crea Copia Conforme")
        self.btn_open = QPushButton("Apri Output")
        self.btn_settings = QPushButton("Impostazioni")
        self.btn_reset = QPushButton("Reset")

        for btn in [self.btn_analyze, self.btn_sanitize, self.btn_open, self.btn_settings, self.btn_reset]:
            button_row.addWidget(btn)
        root.addLayout(button_row)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Log tecnico")
        root.addWidget(self.log)

        self.setCentralWidget(container)

        self.btn_analyze.clicked.connect(self.run_analyze)
        self.btn_sanitize.clicked.connect(self.run_sanitize)
        self.btn_open.clicked.connect(self.open_output)
        self.btn_settings.clicked.connect(self.show_settings)
        self.btn_reset.clicked.connect(self.reset)

    def _set_input_path(self, path: Path) -> None:
        self.input_path = path
        self.log.appendPlainText(f"Input selezionato: {path}")

    def _ensure_input(self) -> bool:
        if self.input_path:
            return True
        selected = QFileDialog.getExistingDirectory(self, "Seleziona cartella di input")
        if not selected:
            return False
        self.input_path = Path(selected)
        return True

    def run_analyze(self) -> None:
        if not self._ensure_input():
            return
        summary = analyze(self.input_path, self.profile)
        self._populate_table(summary)
        self.log.appendPlainText("Analisi completata.")

    def run_sanitize(self) -> None:
        if not self._ensure_input():
            return
        output, summary = sanitize(self.input_path, self.profile)
        self.last_output = output
        self._populate_table(summary)
        self.log.appendPlainText(f"Sanitizzazione completata: {output}")

    def _populate_table(self, summary) -> None:
        self.table.setRowCount(0)
        self.details.clear()
        for result in summary.files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            issues_text = "; ".join(f"{i.level}:{i.code}" for i in result.issues) or "-"

            self.table.setItem(row, 0, QTableWidgetItem(result.source.name))
            self.table.setItem(row, 1, QTableWidgetItem(result.file_type))
            state_item = QTableWidgetItem(result.status.upper())
            if result.status == "ok":
                state_item.setBackground(QColor("#bbf7d0"))
            elif result.status == "warning":
                state_item.setBackground(QColor("#fef08a"))
            else:
                state_item.setBackground(QColor("#fecaca"))
            self.table.setItem(row, 2, state_item)
            self.table.setItem(row, 3, QTableWidgetItem(issues_text))
            self.table.setItem(row, 4, QTableWidgetItem(result.suggested_name or ""))
            self.table.setItem(row, 5, QTableWidgetItem("auto"))

        self.details.setPlainText("\n".join(f"{f.source.name}: {f.status}" for f in summary.files))

    def open_output(self) -> None:
        if not self.last_output:
            QMessageBox.information(self, "Info", "Nessun output disponibile.")
            return
        QMessageBox.information(self, "Output", f"Output disponibile in:\n{self.last_output}")

    def show_settings(self) -> None:
        QMessageBox.information(self, "Impostazioni", "MVP: profilo fisso pdua_safe. CLI supporta --profile.")

    def reset(self) -> None:
        self.input_path = None
        self.last_output = None
        self.table.setRowCount(0)
        self.details.clear()
        self.log.clear()
        self.log.appendPlainText("Stato resettato.")
