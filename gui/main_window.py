from __future__ import annotations

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase
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
from core.models import AnalysisSummary
from core.sanitizer import analyze, sanitize

PROBLEM_HELP = {
    "ext_warning": {
        "title": "Formato da verificare",
        "description": "Il formato è ammesso con cautela nel profilo corrente.",
        "fix": "Preferire PDF/P7M o formati esplicitamente ammessi.",
    },
    "ext_forbidden": {
        "title": "Formato non ammesso",
        "description": "Il file usa un'estensione non prevista per il deposito.",
        "fix": "Convertire il documento in un formato ammesso (es. PDF).",
    },
    "filename_normalize": {
        "title": "Nome file non conforme",
        "description": "Nome con caratteri/spazi non conservativi per PCT/PDUA.",
        "fix": "Usare solo caratteri alfanumerici, -, _, . senza accenti.",
    },
    "zip_nested": {
        "title": "ZIP non flat",
        "description": "Archivio con cartelle interne annidate.",
        "fix": "Estrarre e ricreare ZIP con file tutti in radice.",
    },
    "zip_ext_forbidden": {
        "title": "File vietati nello ZIP",
        "description": "Uno o più file interni hanno estensione non ammessa.",
        "fix": "Rimuovere i file vietati e ricomprimere.",
    },
    "zip_mixed_pades": {
        "title": "Mix firmati/non firmati",
        "description": "Nello stesso ZIP ci sono PDF firmati e non firmati.",
        "fix": "Separare i documenti firmati da quelli non firmati.",
    },
}


class DropArea(QFrame):
    def __init__(self, on_path_dropped):
        super().__init__()
        self.on_path_dropped = on_path_dropped
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 22, 16, 22)
        layout.setSpacing(8)

        icon = QLabel("📂")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_font = QFont(icon.font())
        icon_font.setPointSize(28)
        icon.setFont(icon_font)

        title = QLabel("Trascina qui file/cartella da analizzare")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont(title.font())
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel("Oppure usa i pulsanti sottostanti")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)

    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragActive", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):  # noqa: N802
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):  # noqa: N802
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)

        urls = event.mimeData().urls()
        if not urls:
            return
        paths = [Path(url.toLocalFile()) for url in urls if url.toLocalFile()]
        self.on_path_dropped(paths)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GD LEX – Verifica Deposito PCT/PDUA")
        self.resize(1180, 800)

        self.input_path: Path | None = None
        self.last_output: Path | None = None
        self.last_summary: AnalysisSummary | None = None
        self._temp_input_dir: Path | None = None

        self.settings = QSettings("GD LEX", "PCT-PDUA-Validator")
        self.config = load_config()
        self.profile = resolve_profile(self.config, "pdua_safe")

        self._setup_styles()
        self._build_ui()
        self._restore_settings()

    def _setup_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
              background: #1e1e1e;
              color: #eaeaea;
              font-size: 10.5pt;
            }
            QFrame#DropZone {
              background: #232323;
              border: 2px dashed #3a3a3a;
              border-radius: 10px;
            }
            QFrame#DropZone:hover, QFrame#DropZone[dragActive="true"] {
              border-color: #3daee9;
            }
            QTableWidget {
              background: #262626;
              alternate-background-color: #2a2a2a;
              gridline-color: #3a3a3a;
              color: #eaeaea;
              selection-background-color: #3daee9;
              selection-color: #0b0b0b;
            }
            QTableWidget::item:hover {
              background: #303030;
            }
            QHeaderView::section {
              background: #2d2d2d;
              color: #eaeaea;
              font-weight: 700;
              padding: 8px;
              border: 0px;
            }
            QPlainTextEdit {
              background: #232323;
              color: #eaeaea;
              border: 1px solid #3a3a3a;
              selection-background-color: #3daee9;
              selection-color: #0b0b0b;
            }
            QPushButton {
              border-radius: 6px;
              padding: 8px;
              background: #2a2a2a;
              color: #eaeaea;
              border: 1px solid #3a3a3a;
            }
            QPushButton:hover {
              border: 1px solid #3daee9;
            }
            QPushButton#PrimaryButton {
              background: #3daee9;
              color: #0b0b0b;
              font-weight: 700;
            }
            QPushButton#SecondaryButton {
              background: #4da269;
              color: #eaeaea;
              font-weight: 700;
            }
            QPushButton#DangerButton {
              background: #d64545;
              color: #ffffff;
              font-weight: 700;
            }
            """
        )

    def _build_ui(self) -> None:
        container = QWidget()
        root = QVBoxLayout(container)

        self.drop_area = DropArea(self._set_input_paths)
        root.addWidget(self.drop_area)

        load_row = QHBoxLayout()
        self.btn_load_file = QPushButton("Carica file…")
        self.btn_load_folder = QPushButton("Carica cartella…")
        load_row.addWidget(self.btn_load_file)
        load_row.addWidget(self.btn_load_folder)
        load_row.addStretch(1)
        root.addLayout(load_row)

        self.table = QTableWidget(0, 7)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalHeaderLabels(
            ["Originale", "Tipo", "Stato", "Problemi", "Nuovo Nome", "Esito correzione", "Azioni"]
        )
        table_font = QFont(self.table.font())
        table_font.setPointSize(max(table_font.pointSize(), 11))
        self.table.setFont(table_font)
        root.addWidget(self.table)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Dettagli tecnici selezione file")
        root.addWidget(self.details)

        button_row = QHBoxLayout()
        self.btn_analyze = QPushButton("Analizza")
        self.btn_analyze.setObjectName("PrimaryButton")
        self.btn_sanitize = QPushButton("Correggi automaticamente")
        self.btn_sanitize.setObjectName("SecondaryButton")
        self.btn_sanitize.setEnabled(False)
        self.btn_open = QPushButton("Apri Output")
        self.btn_copy_report = QPushButton("Copia report")
        self.btn_settings = QPushButton("Impostazioni")
        self.btn_reset = QPushButton("Reset / Clear")
        self.btn_reset.setObjectName("DangerButton")

        for btn in [self.btn_analyze, self.btn_sanitize, self.btn_open, self.btn_copy_report, self.btn_settings, self.btn_reset]:
            button_row.addWidget(btn)
        root.addLayout(button_row)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Log tecnico")
        self.log.setStyleSheet("QPlainTextEdit { color: #9aa4b2; }")
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.log.setFont(fixed_font)
        root.addWidget(self.log)

        self.setCentralWidget(container)

        self.btn_load_file.clicked.connect(self.choose_files)
        self.btn_load_folder.clicked.connect(self.choose_folder)
        self.btn_analyze.clicked.connect(self.run_analyze)
        self.btn_sanitize.clicked.connect(self.run_sanitize)
        self.btn_open.clicked.connect(self.open_output)
        self.btn_copy_report.clicked.connect(self.copy_report)
        self.btn_settings.clicked.connect(self.show_settings)
        self.btn_reset.clicked.connect(self.reset)

    def choose_files(self) -> None:
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleziona file di input",
            str(self.input_path.parent) if self.input_path and self.input_path.is_file() else "",
            "Documenti supportati (*.pdf *.zip);;Tutti i file (*)",
        )
        if selected_files:
            self._set_input_paths([Path(p) for p in selected_files])

    def choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Seleziona cartella di input",
            str(self.input_path) if self.input_path and self.input_path.is_dir() else "",
        )
        if selected:
            self._set_input_paths([Path(selected)])

    def _set_input_paths(self, paths: list[Path]) -> None:
        valid = [p for p in paths if p.exists()]
        if not valid:
            self._append_log("Input non valido.")
            return

        if self._temp_input_dir and self._temp_input_dir.exists():
            shutil.rmtree(self._temp_input_dir, ignore_errors=True)
            self._temp_input_dir = None

        if len(valid) == 1:
            self.input_path = valid[0]
            self.settings.setValue("last_input", str(self.input_path))
            self._append_log(f"Input selezionato: {self.input_path}")
            return

        temp_dir = Path(tempfile.mkdtemp(prefix="gdlex_multi_"))
        for src in valid:
            if src.is_file():
                shutil.copy2(src, temp_dir / src.name)
        self._temp_input_dir = temp_dir
        self.input_path = temp_dir
        self.settings.setValue("last_input", str(self.input_path))
        self._append_log(f"Input multiplo caricato ({len(valid)} file).")

    def _ensure_input(self) -> bool:
        if self.input_path:
            return True
        self.choose_folder()
        if self.input_path:
            return True
        self.choose_files()
        return self.input_path is not None

    def run_analyze(self) -> None:
        if not self._ensure_input():
            return
        summary = analyze(self.input_path, self.profile)
        self.last_summary = summary
        self._populate_table(summary)
        self.btn_sanitize.setEnabled(True)
        self._append_log("Analisi completata.")

    def run_sanitize(self) -> None:
        if not self._ensure_input():
            return
        output, summary = sanitize(self.input_path, self.profile)
        self.last_output = output

        refreshed = analyze(output, self.profile) if output else summary
        by_name = {item.source.name: item for item in summary.files}
        for file_result in refreshed.files:
            source_name = Path(file_result.source.name).name
            if source_name in by_name:
                file_result.correction_outcome = by_name[source_name].correction_outcome
                file_result.correction_actions = by_name[source_name].correction_actions

        self.last_summary = refreshed
        if output is not None:
            self.settings.setValue("last_output", str(output))
        self._populate_table(refreshed)
        self._append_log(f"Correzione completata: {output}")

    def _status_badge(self, status: str) -> tuple[str, QColor]:
        mapping = {
            "ok": ("🟢 OK", QColor("#2f6f44")),
            "warning": ("🟠 WARNING", QColor("#5e4b1f")),
            "error": ("🔴 ERROR", QColor("#5f2525")),
        }
        return mapping.get(status, (status.upper(), QColor("#2a2a2a")))

    def _tooltip_for_issues(self, issues: list) -> str:
        if not issues:
            return "<b>Nessun problema rilevato</b>"
        chunks = []
        for issue in issues:
            entry = PROBLEM_HELP.get(
                issue.code,
                {
                    "title": issue.code,
                    "description": issue.message,
                    "fix": "Valutare intervento manuale.",
                },
            )
            chunks.append(
                f"<b>{entry['title']}</b><br>"
                f"{entry['description']}<br>"
                f"<i>Come risolvere:</i> {entry['fix']}"
            )
        return "<hr>".join(chunks)

    def _status_tooltip(self, status: str) -> str:
        info = {
            "ok": "Documento conforme o non bloccante.",
            "warning": "Documento con aspetti da controllare prima del deposito.",
            "error": "Documento non conforme o potenzialmente non depositabile.",
        }
        return info.get(status, "Stato non disponibile")

    def _populate_table(self, summary: AnalysisSummary) -> None:
        self.table.setRowCount(0)
        self.details.clear()
        for result in summary.files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            issues_text = "; ".join(f"{i.level}:{i.code}" for i in result.issues) or "-"

            self.table.setItem(row, 0, QTableWidgetItem(result.source.name))
            self.table.setItem(row, 1, QTableWidgetItem(result.file_type))

            badge, tint = self._status_badge(result.status)
            state_item = QTableWidgetItem(badge)
            state_item.setBackground(tint)
            state_item.setToolTip(self._status_tooltip(result.status))
            self.table.setItem(row, 2, state_item)

            self.table.setItem(row, 3, QTableWidgetItem(issues_text))
            self.table.item(row, 3).setToolTip(self._tooltip_for_issues(result.issues))

            self.table.setItem(row, 4, QTableWidgetItem(result.suggested_name or ""))
            self.table.item(row, 4).setToolTip(result.suggested_name or "")

            correction = result.correction_outcome or ""
            self.table.setItem(row, 5, QTableWidgetItem(correction))

            actions = " | ".join(result.correction_actions) if result.correction_actions else "auto"
            self.table.setItem(row, 6, QTableWidgetItem(actions))

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
            lines.append(f"{item.source.name}: {item.status.upper()} | {item.correction_outcome or 'N/D'}")
            for issue in item.issues:
                lines.append(f"  - [{issue.level.upper()}] {issue.code}: {issue.message}")
            for action in item.correction_actions:
                lines.append(f"    * {action}")

        QApplication.clipboard().setText("\n".join(lines))
        self._append_log("Report copiato negli appunti.")

    def show_settings(self) -> None:
        QMessageBox.information(self, "Impostazioni", "MVP: profilo fisso pdua_safe. CLI supporta --profile.")

    def reset(self) -> None:
        self.input_path = None
        self.last_output = None
        self.last_summary = None
        self.btn_sanitize.setEnabled(False)
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

        if self._temp_input_dir and self._temp_input_dir.exists():
            shutil.rmtree(self._temp_input_dir, ignore_errors=True)

        super().closeEvent(event)
