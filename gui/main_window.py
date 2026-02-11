from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QFontDatabase, QPalette
from PySide6.QtWidgets import (
    QApplication,
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
        self.last_summary = None
        self.settings = QSettings("GD LEX", "PCT-PDUA-Validator")

        self.config = load_config()
        self.profile = resolve_profile(self.config, "pdua_safe")

        self._setup_palette()
        self._build_ui()
        self._restore_settings()

    def _setup_palette(self) -> None:
        palette = QPalette()

        # GD LEX "light" sobrio
        window = QColor("#f1f5f9")
        base = QColor("#ffffff")
        alt_base = QColor("#f8fafc")
        text = QColor("#0f172a")
        disabled_text = QColor("#64748b")

        button = QColor("#0f172a")
        button_text = QColor("#ffffff")

        highlight = QColor("#2563eb")
        highlighted_text = QColor("#ffffff")

        palette.setColor(QPalette.ColorRole.Window, window)
        palette.setColor(QPalette.ColorRole.WindowText, text)
        palette.setColor(QPalette.ColorRole.Base, base)
        palette.setColor(QPalette.ColorRole.AlternateBase, alt_base)
        palette.setColor(QPalette.ColorRole.Text, text)
        palette.setColor(QPalette.ColorRole.Button, button)
        palette.setColor(QPalette.ColorRole.ButtonText, button_text)
        palette.setColor(QPalette.ColorRole.Highlight, highlight)
        palette.setColor(QPalette.ColorRole.HighlightedText, highlighted_text)

        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_text)

        self.setPalette(palette)

        # “cintura e bretelle”: assicura contrasto in tabella e editor anche su tema/override strani
        self.setStyleSheet("""
            QTableWidget { background: #ffffff; color: #0f172a; gridline-color: #e5e7eb; }
            QTableWidget::item { color: #0f172a; }
            QHeaderView::section {
                background: #0f172a;
                color: #ffffff;
                padding: 6px;
                border: 0px;
            }
            QPlainTextEdit { background: #ffffff; color: #0f172a; border: 1px solid #e5e7eb; }
        """)

    def _build_ui(self) -> None:
        container = QWidget()
        root = QVBoxLayout(container)

        self.drop_area = DropArea(self._set_input_path)
        root.addWidget(self.drop_area)

        self.table = QTableWidget(0, 6)
        self.table.setAlternatingRowColors(True)
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
        self.btn_copy_report = QPushButton("Copia report")
        self.btn_settings = QPushButton("Impostazioni")
        self.btn_reset = QPushButton("Reset")

        for btn in [self.btn_analyze, self.btn_sanitize, self.btn_open, self.btn_copy_report, self.btn_settings, self.btn_reset]:
            button_row.addWidget(btn)
        root.addLayout(button_row)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Log tecnico")
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.log.setFont(fixed_font)
        root.addWidget(self.log)

        self.setCentralWidget(container)

        self.btn_analyze.clicked.connect(self.run_analyze)
        self.btn_sanitize.clicked.connect(self.run_sanitize)
        self.btn_open.clicked.connect(self.open_output)
        self.btn_copy_report.clicked.connect(self.copy_report)
        self.btn_settings.clicked.connect(self.show_settings)
        self.btn_reset.clicked.connect(self.reset)

    def _set_input_path(self, path: Path) -> None:
        if not path.exists():
            self._append_log(f"Input non valido: {path}")
            return
        self.input_path = path
        self._append_log(f"Input selezionato: {path}")

    def _ensure_input(self) -> bool:
        if self.input_path:
            return True
        selected = QFileDialog.getExistingDirectory(self, "Seleziona cartella di input")
        if selected:
            self.input_path = Path(selected)
            self.settings.setValue("last_input", str(self.input_path))
            return True

        selected_file, _ = QFileDialog.getOpenFileName(self, "Seleziona file di input")
        if not selected_file:
            return False
        self.input_path = Path(selected_file)
        self.settings.setValue("last_input", str(self.input_path))
        return True

    def run_analyze(self) -> None:
        if not self._ensure_input():
            return
        summary = analyze(self.input_path, self.profile)
        self.last_summary = summary
        self._populate_table(summary)
        self._append_log("Analisi completata.")

    def run_sanitize(self) -> None:
        if not self._ensure_input():
            return
        output, summary = sanitize(self.input_path, self.profile)
        self.last_output = output
        self.last_summary = summary
        if self.input_path is not None:
            self.settings.setValue("last_input", str(self.input_path))
        if output is not None:
            self.settings.setValue("last_output", str(output))
        self._populate_table(summary)
        self._append_log(f"Sanitizzazione completata: {output}")

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

            self.table.item(row, 3).setToolTip(issues_text)
            self.table.item(row, 4).setToolTip(result.suggested_name or "")

        self.details.setPlainText("\n".join(f"{f.source.name}: {f.status}" for f in summary.files))
        self._resize_columns_with_cap(max_width=420)

    def open_output(self) -> None:
        if not self.last_output:
            QMessageBox.information(self, "Info", "Nessun output disponibile.")
            return
        QMessageBox.information(self, "Output", f"Output disponibile in:\n{self.last_output}")

    def copy_report(self) -> None:
        if self.last_summary is None:
            QMessageBox.information(self, "Info", "Nessun report disponibile. Eseguire prima un'analisi.")
            return

        lines: list[str] = ["GD LEX - Report sintetico", "=" * 32]
        for item in self.last_summary.files:
            lines.append(f"{item.source.name}: {item.status.upper()}")
            for issue in item.issues:
                lines.append(f"  - [{issue.level.upper()}] {issue.code}: {issue.message}")

        report_text = "\n".join(lines)
        QApplication.clipboard().setText(report_text)
        self._append_log("Report copiato negli appunti.")

    def show_settings(self) -> None:
        QMessageBox.information(self, "Impostazioni", "MVP: profilo fisso pdua_safe. CLI supporta --profile.")

    def reset(self) -> None:
        self.input_path = None
        self.last_output = None
        self.last_summary = None
        self.table.setRowCount(0)
        self.details.clear()
        self.log.clear()
        self._append_log("Stato resettato.")

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log.appendPlainText(f"[{stamp}] {message}")

    def _resize_columns_with_cap(self, max_width: int = 420) -> None:
        self.table.resizeColumnsToContents()
        header = self.table.horizontalHeader()
        for index in range(self.table.columnCount()):
            if header.sectionSize(index) > max_width:
                header.resizeSection(index, max_width)

    def _restore_settings(self) -> None:
        geometry = self.settings.value("window_geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

        saved_input = self.settings.value("last_input")
        if saved_input:
            candidate = Path(saved_input)
            if candidate.exists():
                self.input_path = candidate

        saved_output = self.settings.value("last_output")
        if saved_output:
            output_candidate = Path(saved_output)
            if output_candidate.exists():
                self.last_output = output_candidate

        for index in range(self.table.columnCount()):
            width = self.settings.value(f"col_width_{index}")
            if width is not None:
                self.table.setColumnWidth(index, int(width))

    def closeEvent(self, event):  # noqa: N802
        self.settings.setValue("window_geometry", self.saveGeometry())
        if self.input_path is not None:
            self.settings.setValue("last_input", str(self.input_path))
        if self.last_output is not None:
            self.settings.setValue("last_output", str(self.last_output))
        for index in range(self.table.columnCount()):
            self.settings.setValue(f"col_width_{index}", self.table.columnWidth(index))
        super().closeEvent(event)
