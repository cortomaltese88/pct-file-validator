from __future__ import annotations

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config import load_config, resolve_profile
from core.models import AnalysisSummary
from core.sanitizer import (
    OUTCOME_ERROR,
    OUTCOME_FIXED,
    OUTCOME_IMPOSSIBLE,
    OUTCOME_NOT_RUN,
    OUTCOME_OK,
    OUTCOME_PARTIAL,
    analyze,
    sanitize,
)

PROBLEM_HELP = {
    "ext_warning": {
        "title": "Formato da verificare",
        "description": "Il formato è ammesso con cautela nel profilo corrente: verificare compatibilità col deposito.",
        "fix": "Quando possibile convertire in PDF/P7M e mantenere naming conservativo.",
        "app_action": "In correzione automatica il file viene copiato in output e rianalizzato.",
    },
    "ext_forbidden": {
        "title": "Formato non ammesso",
        "description": "Il file non è pronto per il deposito nel formato attuale.",
        "fix": "Convertire il documento in un formato ammesso e rieseguire analisi.",
        "app_action": "Il file viene marcato IMPOSSIBILE e lasciato fuori dalla correzione.",
    },
    "filename_normalize": {
        "title": "Nome file non conforme",
        "description": "Il nome del file può creare problemi in fase di deposito.",
        "fix": "Usare nome semplice senza spazi/accenti e con caratteri consentiti.",
        "app_action": "In output il nome viene normalizzato automaticamente con gestione collisioni.",
    },
    "zip_nested": {
        "title": "ZIP non flat",
        "description": "L'archivio contiene cartelle interne, struttura non ideale per il deposito.",
        "fix": "Ricreare ZIP con tutti i file in radice.",
        "app_action": "La correzione estrae lo ZIP e lo ricompone in formato flat.",
    },
    "zip_ext_forbidden": {
        "title": "File vietati nello ZIP",
        "description": "Sono presenti file non utilizzabili per il deposito telematico.",
        "fix": "Rimuovere i file non ammessi e ricostruire l'archivio.",
        "app_action": "I file vietati vengono esclusi; se il problema persiste l'esito è IMPOSSIBILE.",
    },
    "zip_mixed_pades": {
        "title": "Mix firmati/non firmati",
        "description": "Nello ZIP sono mescolati PDF firmati e non firmati.",
        "fix": "Separare i documenti firmati da quelli non firmati.",
        "app_action": "Il warning viene mantenuto come informazione non bloccante.",
    },
    "smart_rename_applied": {
        "title": "Smart rename applicato",
        "description": "Il nome file è stato reso più parlante per deposito e gestione pratica.",
        "fix": "Nessuna azione richiesta: verificare solo la coerenza descrittiva.",
        "app_action": "L'app ha rinominato il file in output mantenendo estensione e tracciabilità.",
    },
    "path_too_long_mitigated": {
        "title": "Path troppo lungo mitigato",
        "description": "Il nome è stato accorciato per evitare problemi tipici in OneDrive/cartelle annidate.",
        "fix": "Mantenere strutture cartella più corte e limitare profondità percorsi.",
        "app_action": "L'app ha ridotto il basename per rientrare nella soglia di sicurezza path.",
    },
}


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget, output_mode: str, custom_output_dir: str, smart_enabled: bool, max_filename_len: int, max_output_path_len: int):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni output")
        self.resize(560, 220)

        root = QVBoxLayout(self)

        self.rb_sibling = QRadioButton("Output accanto all'input (default)")
        self.rb_custom = QRadioButton("Output in cartella personalizzata")
        self.rb_sibling.setChecked(output_mode != "custom")
        self.rb_custom.setChecked(output_mode == "custom")

        root.addWidget(self.rb_sibling)
        root.addWidget(self.rb_custom)

        custom_row = QHBoxLayout()
        self.edit_custom = QLineEdit(custom_output_dir)
        self.edit_custom.setPlaceholderText("Seleziona cartella output personalizzata")
        self.btn_browse = QPushButton("Sfoglia…")
        custom_row.addWidget(self.edit_custom)
        custom_row.addWidget(self.btn_browse)
        root.addLayout(custom_row)

        self.chk_smart = QCheckBox("Smart rename attivo")
        self.chk_smart.setChecked(smart_enabled)
        root.addWidget(self.chk_smart)

        smart_row = QHBoxLayout()
        self.spin_max_filename = QSpinBox()
        self.spin_max_filename.setRange(20, 255)
        self.spin_max_filename.setValue(max_filename_len)
        self.spin_max_output_path = QSpinBox()
        self.spin_max_output_path.setRange(80, 400)
        self.spin_max_output_path.setValue(max_output_path_len)
        smart_row.addWidget(QLabel("Max filename len"))
        smart_row.addWidget(self.spin_max_filename)
        smart_row.addSpacing(10)
        smart_row.addWidget(QLabel("Max output path len"))
        smart_row.addWidget(self.spin_max_output_path)
        smart_row.addStretch(1)
        root.addLayout(smart_row)

        self.note = QLabel(
            "Modalità sibling: <dirname(input)>/_PCT_READY_YYYYMMDD_HHMMSS/\n"
            "Modalità custom: <custom_output_dir>/<basename(input)>_PCT_READY_YYYYMMDD_HHMMSS/"
        )
        self.note.setStyleSheet("QLabel { color: #9aa4b2; }")
        root.addWidget(self.note)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_cancel = QPushButton("Annulla")
        self.btn_save = QPushButton("Salva")
        self.btn_save.setObjectName("PrimaryButton")
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_save)
        root.addLayout(actions)

        self.btn_browse.clicked.connect(self._browse_dir)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)

        self._update_enabled_state()
        self.rb_sibling.toggled.connect(self._update_enabled_state)

    def _browse_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Seleziona cartella output")
        if selected:
            self.edit_custom.setText(selected)

    def _update_enabled_state(self) -> None:
        enabled = self.rb_custom.isChecked()
        self.edit_custom.setEnabled(enabled)
        self.btn_browse.setEnabled(enabled)

    def values(self) -> tuple[str, str, bool, int, int]:
        mode = "custom" if self.rb_custom.isChecked() else "sibling"
        return mode, self.edit_custom.text().strip(), self.chk_smart.isChecked(), self.spin_max_filename.value(), self.spin_max_output_path.value()


class DropArea(QFrame):
    def __init__(self, on_path_dropped):
        super().__init__()
        self.on_path_dropped = on_path_dropped
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        icon = QLabel("📂")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_font = QFont(icon.font())
        icon_font.setPointSize(22)
        icon.setFont(icon_font)

        title = QLabel("Trascina qui file/cartella da analizzare")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont(title.font())
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel("Oppure usa i pulsanti sottostanti")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("QLabel { color: #9aa4b2; }")

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
        self.output_mode = self.settings.value("output_mode", "sibling")
        self.custom_output_dir = self.settings.value("custom_output_dir", "")
        self.smart_rename_enabled = self.settings.value("smart_rename_enabled", True, type=bool)
        self.max_filename_len = int(self.settings.value("max_filename_len", 60))
        self.max_output_path_len = int(self.settings.value("max_output_path_len", 180))

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
              border: 2px dashed #3daee9;
              border-radius: 12px;
            }
            QFrame#DropZone:hover, QFrame#DropZone[dragActive="true"] {
              border-color: #59c7ff;
              background: rgba(61, 174, 233, 0.12);
            }
            QTableWidget {
              background: #262626;
              alternate-background-color: #2a2a2a;
              gridline-color: #3a3a3a;
              color: #eaeaea;
              selection-background-color: #3daee9;
              selection-color: #0b0b0b;
            }
            QTableWidget::item {
              padding: 6px;
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
              min-height: 40px;
              border-radius: 6px;
              padding: 8px 12px;
              background: #2a2a2a;
              color: #eaeaea;
              border: 1px solid #3a3a3a;
            }
            QPushButton:hover {
              border: 1px solid #59c7ff;
              background: #363636;
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
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.drop_area = DropArea(self._set_input_paths)
        root.addWidget(self.drop_area)

        load_row = QHBoxLayout()
        load_row.setSpacing(10)
        self.btn_load_file = QPushButton("Carica file…")
        self.btn_load_folder = QPushButton("Carica cartella…")
        load_row.addWidget(self.btn_load_file)
        load_row.addWidget(self.btn_load_folder)
        load_row.addStretch(1)
        root.addLayout(load_row)

        self.splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 7)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalHeaderLabels(
            ["Originale", "Tipo", "Stato", "Problemi", "Nuovo Nome", "Esito correzione", "Azioni"]
        )
        self.table.verticalHeader().setDefaultSectionSize(36)
        table_font = QFont(self.table.font())
        table_font.setPointSize(max(table_font.pointSize(), 11))
        self.table.setFont(table_font)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Dettagli tecnici selezione file")

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Log tecnico")
        self.log.setStyleSheet("QPlainTextEdit { color: #9aa4b2; }")
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.log.setFont(fixed_font)

        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.details)
        self.splitter.addWidget(self.log)
        self.splitter.setChildrenCollapsible(False)
        root.addWidget(self.splitter)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.btn_analyze = QPushButton("Analizza")
        self.btn_analyze.setObjectName("PrimaryButton")
        self.btn_sanitize = QPushButton("Correggi automaticamente")
        self.btn_sanitize.setObjectName("SecondaryButton")
        self.btn_sanitize.setEnabled(False)
        self.btn_open = QPushButton("Apri Output")
        self.btn_open_report = QPushButton("Apri report tecnico")
        self.btn_copy_report = QPushButton("Copia report")
        self.btn_settings = QPushButton("Impostazioni")
        self.btn_reset = QPushButton("Reset / Clear")
        self.btn_reset.setObjectName("DangerButton")

        for btn in [self.btn_analyze, self.btn_sanitize, self.btn_open, self.btn_open_report, self.btn_copy_report, self.btn_settings, self.btn_reset]:
            button_row.addWidget(btn)
        root.addLayout(button_row)

        self.setCentralWidget(container)

        self.btn_load_file.clicked.connect(self.choose_files)
        self.btn_load_folder.clicked.connect(self.choose_folder)
        self.btn_analyze.clicked.connect(self.run_analyze)
        self.btn_sanitize.clicked.connect(self.run_sanitize)
        self.btn_open.clicked.connect(self.open_output)
        self.btn_open_report.clicked.connect(self.open_report_technical)
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
        output, summary = sanitize(
            self.input_path,
            self.profile,
            output_mode=str(self.output_mode),
            custom_output_dir=Path(self.custom_output_dir) if self.custom_output_dir else None,
            smart_opts={
                "enabled": self.smart_rename_enabled,
                "max_filename_len": self.max_filename_len,
                "max_output_path_len": self.max_output_path_len,
            },
        )
        self.last_output = output

        refreshed = analyze(output, self.profile) if output else summary
        by_name = {item.source.name: item for item in summary.files}
        for file_result in refreshed.files:
            source_name = Path(file_result.source.name).name
            if source_name in by_name:
                file_result.correction_outcome = by_name[source_name].correction_outcome
                file_result.correction_actions = by_name[source_name].correction_actions
                file_result.output_path = by_name[source_name].output_path

        self.last_summary = refreshed
        if output is not None:
            self.settings.setValue("last_output", str(output))
        self._populate_table(refreshed)
        self._append_log(f"Correzione completata: {output}")
        for file_result in refreshed.files:
            target = str(file_result.output_path) if file_result.output_path else "n/d"
            self._append_log(f"{file_result.source.name}: {file_result.correction_outcome} -> {target}")

    def _status_badge(self, status: str) -> tuple[str, QColor, QColor]:
        mapping = {
            "ok": (" OK ", QColor("#2e8b57"), QColor("#ffffff")),
            "warning": (" WARNING ", QColor("#f39c12"), QColor("#1b1b1b")),
            "error": (" ERROR ", QColor("#d64545"), QColor("#ffffff")),
        }
        return mapping.get(status, (status.upper(), QColor("#2a2a2a"), QColor("#eaeaea")))

    def _tooltip_for_issues(self, issues: list) -> str:
        if not issues:
            return (
                "<b>Nessuna criticità operativa.</b><br>"
                "Il file risulta utilizzabile nel flusso di preparazione deposito."
            )
        chunks = []
        for issue in issues:
            entry = PROBLEM_HELP.get(
                issue.code,
                {
                    "title": issue.code,
                    "description": issue.message,
                    "fix": "Intervenire manualmente e ripetere l'analisi.",
                },
            )
            chunks.append(
                f"<b>{entry['title']}</b><br>"
                f"{entry['description']}<br>"
                f"<i>Azione consigliata:</i> {entry['fix']}<br>"
                f"<i>Cosa fa l'app:</i> {entry.get('app_action', 'Segnala nel report tecnico.')}"
            )
        return "<hr>".join(chunks)

    def _status_tooltip(self, status: str) -> str:
        info = {
            "ok": "Stato OK: file pronto o comunque non bloccante per il deposito.",
            "warning": "Stato WARNING: richiede verifica operativa prima dell'invio.",
            "error": "Stato ERROR: il file va corretto perché può bloccare il deposito.",
        }
        return info.get(status, "Stato non disponibile")

    def _correction_tooltip(self, outcome: str) -> str:
        mapping = {
            OUTCOME_NOT_RUN: "Correzione non ancora avviata su questo file.",
            OUTCOME_OK: "Nessuna modifica necessaria: file già coerente.",
            OUTCOME_FIXED: "Correzione automatica completata con esito positivo.",
            OUTCOME_PARTIAL: "Correzione parziale: residuano elementi da verificare.",
            OUTCOME_IMPOSSIBLE: "Intervento automatico non possibile, serve azione manuale.",
            OUTCOME_ERROR: "Errore in fase di correzione: verificare log tecnico.",
        }
        return mapping.get(outcome, "Esito non disponibile")

    def _populate_table(self, summary: AnalysisSummary) -> None:
        self.table.setRowCount(0)
        self.details.clear()
        for result in summary.files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            issues_text = "; ".join(f"{i.level}:{i.code}" for i in result.issues) or "-"

            self.table.setItem(row, 0, QTableWidgetItem(result.source.name))
            self.table.setItem(row, 1, QTableWidgetItem(result.file_type))

            badge, bg, fg = self._status_badge(result.status)
            state_item = QTableWidgetItem(badge)
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            state_item.setBackground(bg)
            state_item.setForeground(fg)
            state_item.setToolTip(self._status_tooltip(result.status))
            self.table.setItem(row, 2, state_item)

            self.table.setItem(row, 3, QTableWidgetItem(issues_text))
            self.table.item(row, 3).setToolTip(self._tooltip_for_issues(result.issues))

            self.table.setItem(row, 4, QTableWidgetItem(result.suggested_name or ""))
            self.table.item(row, 4).setToolTip(result.suggested_name or "Nome non suggerito")

            correction = result.correction_outcome or OUTCOME_NOT_RUN
            correction_item = QTableWidgetItem(correction)
            correction_item.setToolTip(self._correction_tooltip(correction))
            self.table.setItem(row, 5, correction_item)

            actions = " | ".join(result.correction_actions) if result.correction_actions else "auto"
            self.table.setItem(row, 6, QTableWidgetItem(actions))

        detail_lines = [f"{f.source.name}: {f.status}" for f in summary.files]
        if self.last_output:
            detail_lines.append("")
            detail_lines.append(f"Output depositabile: {self.last_output}")
            detail_lines.append(f"Report tecnico: {self.last_output / '.gdlex'}")
        self.details.setPlainText("\n".join(detail_lines))
        self._resize_columns_with_cap(max_width=420)


    def _technical_dir(self) -> Path | None:
        if not self.last_output:
            return None
        return self.last_output / ".gdlex"

    def open_output(self) -> None:
        if not self.last_output:
            QMessageBox.information(self, "Info", "Nessun output disponibile.")
            return
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))
        if not ok:
            QMessageBox.information(self, "Output", f"Output disponibile in:\n{self.last_output}")

    def open_report_technical(self) -> None:
        tech = self._technical_dir()
        if not tech or not tech.exists():
            QMessageBox.information(self, "Info", "Nessun report tecnico disponibile.")
            return
        txt = tech / "REPORT.txt"
        target = txt if txt.exists() else tech
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        if not ok:
            QMessageBox.information(self, "Report tecnico", f"Report disponibili in:\n{tech}")

    def copy_report(self) -> None:
        if self.last_summary is None:
            QMessageBox.information(self, "Info", "Nessun report disponibile. Eseguire prima un'analisi.")
            return

        lines: list[str] = ["GD LEX - Report sintetico", "=" * 32]
        for item in self.last_summary.files:
            lines.append(f"{item.source.name}: {item.status.upper()} | {item.correction_outcome or OUTCOME_NOT_RUN}")
            for issue in item.issues:
                lines.append(f"  - [{issue.level.upper()}] {issue.code}: {issue.message}")
            for action in item.correction_actions:
                lines.append(f"    * {action}")

        QApplication.clipboard().setText("\n".join(lines))
        self._append_log("Report copiato negli appunti.")

    def show_settings(self) -> None:
        dialog = SettingsDialog(
            self,
            self.output_mode,
            self.custom_output_dir,
            self.smart_rename_enabled,
            self.max_filename_len,
            self.max_output_path_len,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            mode, custom_dir, smart_enabled, max_filename_len, max_output_path_len = dialog.values()
            self.output_mode = mode
            self.custom_output_dir = custom_dir
            self.smart_rename_enabled = smart_enabled
            self.max_filename_len = max_filename_len
            self.max_output_path_len = max_output_path_len
            self.settings.setValue("output_mode", self.output_mode)
            self.settings.setValue("custom_output_dir", self.custom_output_dir)
            self.settings.setValue("smart_rename_enabled", self.smart_rename_enabled)
            self.settings.setValue("max_filename_len", self.max_filename_len)
            self.settings.setValue("max_output_path_len", self.max_output_path_len)
            self._append_log(
                f"Impostazioni salvate: output_mode={self.output_mode}, custom_output_dir={self.custom_output_dir or '-'}, smart_rename={self.smart_rename_enabled}, max_filename_len={self.max_filename_len}, max_output_path_len={self.max_output_path_len}"
            )

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

        splitter_sizes = self.settings.value("splitter_sizes")
        if splitter_sizes:
            self.splitter.setSizes([int(v) for v in splitter_sizes])
        else:
            self.splitter.setSizes([60, 20, 20])

        self.output_mode = self.settings.value("output_mode", "sibling")
        self.custom_output_dir = self.settings.value("custom_output_dir", "")
        self.smart_rename_enabled = self.settings.value("smart_rename_enabled", True, type=bool)
        self.max_filename_len = int(self.settings.value("max_filename_len", 60))
        self.max_output_path_len = int(self.settings.value("max_output_path_len", 180))

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
        self.settings.setValue("splitter_sizes", self.splitter.sizes())
        self.settings.setValue("output_mode", self.output_mode)
        self.settings.setValue("custom_output_dir", self.custom_output_dir)
        self.settings.setValue("smart_rename_enabled", self.smart_rename_enabled)
        self.settings.setValue("max_filename_len", self.max_filename_len)
        self.settings.setValue("max_output_path_len", self.max_output_path_len)
        if self.input_path is not None:
            self.settings.setValue("last_input", str(self.input_path))
        if self.last_output is not None:
            self.settings.setValue("last_output", str(self.last_output))
        for index in range(self.table.columnCount()):
            self.settings.setValue(f"col_width_{index}", self.table.columnWidth(index))

        if self._temp_input_dir and self._temp_input_dir.exists():
            shutil.rmtree(self._temp_input_dir, ignore_errors=True)

        super().closeEvent(event)
