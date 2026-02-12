from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QStandardItem, QStandardItemModel, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
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
    QSplitter,
    QSpinBox,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.config import load_config, resolve_profile
from core.models import AnalysisSummary
from core.reporting import build_synthetic_report, build_technical_report
from core.sanitizer import (
    OUTCOME_ERROR,
    OUTCOME_FIXED,
    OUTCOME_IMPOSSIBLE,
    OUTCOME_NOT_RUN,
    OUTCOME_OK,
    OUTCOME_PARTIAL,
    analyze,
    iter_input_files,
    sanitize,
)

PROBLEM_HELP = {
    "filename_normalize": {
        "title": "Nome file non conforme",
        "description": "Il nome contiene spazi/caratteri non ammessi. In deposito può creare problemi o risultare poco leggibile.",
        "fix": "Autofix: rinomina in formato safe (ASCII/underscore).",
    },
    "filename_invalid_chars": {
        "title": "Caratteri non validi nel nome",
        "description": "Il nome include simboli che possono bloccare o sporcare il deposito.",
        "fix": "Autofix: sostituzione con caratteri safe e underscore.",
    },
    "filename_too_long": {
        "title": "Nome troppo lungo",
        "description": "Basename eccessivo: possibile errore su OneDrive e percorsi profondi.",
        "fix": "Autofix: abbreviazione nome con preservazione estensione.",
    },
    "pades_detected": {
        "title": "Firma PAdES rilevata",
        "description": "PDF firmato rilevato. Non è un errore bloccante.",
        "fix": "Verificare solo coerenza con eventuali documenti non firmati nello stesso ZIP.",
    },
    "zip_name": {
        "title": "Nome interno ZIP non conforme",
        "description": "Uno o più file nello ZIP hanno naming non conforme.",
        "fix": "Autofix: rinomina interna safe durante ricostruzione ZIP.",
    },
    "zip_nested": {
        "title": "ZIP con cartelle interne",
        "description": "Lo ZIP contiene directory annidate; per PCT è preferibile ZIP flat.",
        "fix": "Autofix: estrazione e ricostruzione ZIP senza cartelle.",
    },
    "zip_mixed_pades": {
        "title": "ZIP con firmati/non firmati",
        "description": "Nello stesso archivio coesistono PDF firmati e non firmati.",
        "fix": "Warning non bloccante: separare in due ZIP se richiesto dalla prassi.",
    },
    "ext_forbidden": {
        "title": "Formato non ammesso",
        "description": "L'estensione non è ammessa dal profilo di deposito.",
        "fix": "Autofix: file marcato come IMPOSSIBILE; conversione manuale necessaria.",
    },
    "zip_ext_forbidden": {
        "title": "Estensione non ammessa nello ZIP",
        "description": "Nell'archivio sono presenti file con estensioni non depositabili.",
        "fix": "Autofix: prova esclusione/riparazione, altrimenti esito IMPOSSIBILE.",
    },
    "smart_rename_applied": {
        "title": "Smart rename applicato",
        "description": "Nome file reso più parlante e sicuro per deposito/path lunghi.",
        "fix": "Nessuna azione obbligatoria; verificare il nome finale proposto.",
    },
    "path_too_long_mitigated": {
        "title": "Path lungo mitigato",
        "description": "Ridotta lunghezza nome per evitare problemi OneDrive/cartelle annidate.",
        "fix": "Mantenere percorsi brevi e struttura cartelle poco profonda.",
    },
}


@dataclass(slots=True)
class RowState:
    source_path: str
    original: str
    file_type: str
    status: str
    issues: list = field(default_factory=list)
    new_name: str = ""
    fix_outcome: str = OUTCOME_NOT_RUN
    output_path: str = "-"
    actions: list[str] = field(default_factory=list)


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget, output_mode: str, custom_output_dir: str, smart_enabled: bool, max_filename_len: int, max_output_path_len: int, create_backup: bool):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni output")
        self.resize(620, 260)

        root = QVBoxLayout(self)
        self.chk_sibling = QCheckBox("Output di default accanto all'input")
        self.chk_sibling.setChecked(output_mode != "custom")
        root.addWidget(self.chk_sibling)

        custom_row = QHBoxLayout()
        self.edit_custom = QLineEdit(custom_output_dir)
        self.btn_browse = QPushButton("Sfoglia…")
        custom_row.addWidget(self.edit_custom)
        custom_row.addWidget(self.btn_browse)
        root.addLayout(custom_row)

        self.chk_smart = QCheckBox("Smart rename attivo")
        self.chk_smart.setChecked(smart_enabled)
        root.addWidget(self.chk_smart)

        self.chk_backup = QCheckBox("Crea backup originali in .gdlex (default OFF)")
        self.chk_backup.setChecked(create_backup)
        root.addWidget(self.chk_backup)

        smart_row = QHBoxLayout()
        self.spin_max_filename = QSpinBox()
        self.spin_max_filename.setRange(20, 255)
        self.spin_max_filename.setValue(max_filename_len)
        self.spin_max_output_path = QSpinBox()
        self.spin_max_output_path.setRange(80, 400)
        self.spin_max_output_path.setValue(max_output_path_len)
        smart_row.addWidget(QLabel("Max filename len"))
        smart_row.addWidget(self.spin_max_filename)
        smart_row.addWidget(QLabel("Max output path len"))
        smart_row.addWidget(self.spin_max_output_path)
        smart_row.addStretch(1)
        root.addLayout(smart_row)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_cancel = QPushButton("Annulla")
        self.btn_save = QPushButton("Salva")
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_save)
        root.addLayout(actions)

        self.chk_sibling.toggled.connect(self._sync_custom_state)
        self.btn_browse.clicked.connect(self._browse_dir)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)
        self._sync_custom_state()

    def _sync_custom_state(self) -> None:
        enabled = not self.chk_sibling.isChecked()
        self.edit_custom.setEnabled(enabled)
        self.btn_browse.setEnabled(enabled)

    def _browse_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Seleziona cartella output")
        if selected:
            self.edit_custom.setText(selected)

    def values(self) -> tuple[str, str, bool, int, int, bool]:
        mode = "sibling" if self.chk_sibling.isChecked() else "custom"
        return (
            mode,
            self.edit_custom.text().strip(),
            self.chk_smart.isChecked(),
            self.spin_max_filename.value(),
            self.spin_max_output_path.value(),
            self.chk_backup.isChecked(),
        )


def paths_from_drop_urls(raw_urls: list[str]) -> list[Path]:
    out = []
    for raw in raw_urls:
        if not raw:
            continue
        out.append(Path(raw))
    return out


class DropArea(QFrame):
    def __init__(self, on_path_dropped):
        super().__init__()
        self.on_path_dropped = on_path_dropped
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        icon = QLabel("📂")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(icon.font())
        font.setPointSize(22)
        icon.setFont(font)

        title = QLabel("Trascina qui file/cartella da analizzare")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tfont = QFont(title.font())
        tfont.setPointSize(14)
        tfont.setBold(True)
        title.setFont(tfont)

        subtitle = QLabel("Oppure usa i pulsanti sotto")
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

    def dropEvent(self, event):  # noqa: N802
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        raw = [url.toLocalFile() for url in event.mimeData().urls()]
        self.on_path_dropped(paths_from_drop_urls(raw))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GD LEX – Verifica Deposito PCT/PDUA")
        self.resize(1180, 800)

        self.rows: list[RowState] = []
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
        self.create_backup = self.settings.value("create_backup", False, type=bool)

        self.config = load_config()
        self.profile = resolve_profile(self.config, "pdua_safe")

        self._setup_styles()
        self._build_ui()
        self._restore_settings()

    def _setup_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background: #1e1e1e; color: #eaeaea; font-size: 10.5pt; }
            QFrame#DropZone { background: #232323; border: 2px dashed #3daee9; border-radius: 12px; }
            QFrame#DropZone:hover, QFrame#DropZone[dragActive="true"] { border-color: #59c7ff; background: rgba(61,174,233,0.12); }
            QTableView { background: #262626; alternate-background-color: #2a2a2a; gridline-color: #3a3a3a; selection-background-color: #3daee9; selection-color: #0b0b0b; }
            QHeaderView::section { background: #2d2d2d; color: #eaeaea; font-weight: 700; padding: 8px; border: 0px; }
            QPushButton { min-height: 40px; border-radius: 6px; padding: 8px 12px; background: #2a2a2a; border: 1px solid #3a3a3a; }
            QPushButton:hover { border: 1px solid #59c7ff; background: #363636; }
            QPushButton#PrimaryButton { background: #3daee9; color: #0b0b0b; font-weight: 700; }
            QPushButton#SecondaryButton { background: #4da269; color: #eaeaea; font-weight: 700; }
            QPushButton#DangerButton { background: #d64545; color: #fff; font-weight: 700; }
            QPlainTextEdit { background: #232323; border: 1px solid #3a3a3a; }
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
        self.btn_load_file = QPushButton("Carica file…")
        self.btn_load_folder = QPushButton("Carica cartella…")
        load_row.addWidget(self.btn_load_file)
        load_row.addWidget(self.btn_load_folder)
        load_row.addStretch(1)
        root.addLayout(load_row)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        self.model = QStandardItemModel(0, 8, self)
        self.model.setHorizontalHeaderLabels(["Originale", "Tipo", "Stato", "Problemi", "Nuovo Nome", "Esito correzione", "Output", "Azioni"])
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self._on_table_double_clicked)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)

        self.report_tabs = QTabWidget()
        self.report_synthetic = QPlainTextEdit()
        self.report_synthetic.setReadOnly(True)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.report_synthetic.setFont(mono)
        self.log.setFont(mono)
        self.report_tabs.addTab(self.report_synthetic, "Sintetico")
        self.report_tabs.addTab(self.log, "Tecnico")

        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.details)
        self.splitter.addWidget(self.report_tabs)
        self.splitter.setChildrenCollapsible(False)
        root.addWidget(self.splitter)

        self.summary_label = QLabel("Riepilogo correzione: NON ESEGUITA")
        root.addWidget(self.summary_label)

        button_row = QHBoxLayout()
        self.btn_analyze = QPushButton("Analizza")
        self.btn_analyze.setObjectName("PrimaryButton")
        self.btn_sanitize = QPushButton("Correggi automaticamente")
        self.btn_sanitize.setObjectName("SecondaryButton")
        self.btn_sanitize.setEnabled(False)
        self.btn_open = QPushButton("Apri Output")
        self.btn_open_report = QPushButton("Apri report tecnico")
        self.btn_copy_summary = QPushButton("Copia riepilogo")
        self.btn_copy_report = QPushButton("Copia report")
        self.btn_settings = QPushButton("Impostazioni")
        self.btn_print_report = QPushButton("Stampa report…")
        self.btn_export_pdf = QPushButton("Esporta PDF…")
        self.btn_export_pdf.setIcon(QIcon.fromTheme("application-pdf"))
        self.btn_reset = QPushButton("Reset / Clear")
        self.btn_reset.setObjectName("DangerButton")

        for btn in [self.btn_analyze, self.btn_sanitize, self.btn_open, self.btn_open_report, self.btn_copy_summary, self.btn_copy_report, self.btn_settings, self.btn_print_report, self.btn_export_pdf, self.btn_reset]:
            button_row.addWidget(btn)
        root.addLayout(button_row)

        self.setCentralWidget(container)

        self.btn_load_file.clicked.connect(self.choose_files)
        self.btn_load_folder.clicked.connect(self.choose_folder)
        self.btn_analyze.clicked.connect(self.run_analyze)
        self.btn_sanitize.clicked.connect(self.run_sanitize)
        self.btn_open.clicked.connect(self.open_output)
        self.btn_open_report.clicked.connect(self.open_report_technical)
        self.btn_copy_summary.clicked.connect(self.copy_summary)
        self.btn_copy_report.clicked.connect(self.copy_report)
        self.btn_settings.clicked.connect(self.show_settings)
        self.btn_print_report.clicked.connect(self.print_report)
        self.btn_export_pdf.clicked.connect(self.export_report_pdf)
        self.btn_reset.clicked.connect(self.reset)

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log.appendPlainText(f"[{stamp}] {message}")

    def choose_files(self) -> None:
        selected, _ = QFileDialog.getOpenFileNames(self, "Seleziona file di input", "", "Tutti i file (*)")
        if selected:
            self._set_input_paths([Path(p) for p in selected])

    def choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Seleziona cartella di input")
        if selected:
            self._set_input_paths([Path(selected)])

    def _collect_preview_rows(self, selected_paths: list[Path]) -> list[RowState]:
        allowed_ext = set(self.profile.get("allowed_formats", [])) | set(self.profile.get("warning_formats", []))
        preview_files: list[Path] = []

        for path in selected_paths:
            if path.is_file():
                preview_files.append(path)
                continue
            if path.is_dir():
                files, excluded = iter_input_files(path)
                for excluded_path, reason in excluded:
                    self._append_log(f"Escluso in preview ({reason}): {excluded_path}")
                for fp in files:
                    ext = fp.suffix.lower().lstrip(".")
                    if ext in allowed_ext:
                        preview_files.append(fp)

        rows: list[RowState] = []
        for fp in preview_files:
            rows.append(
                RowState(
                    source_path=str(fp),
                    original=fp.name,
                    file_type=fp.suffix.lower().lstrip(".") or "file",
                    status="non_analizzato",
                    issues=[],
                    new_name=fp.name,
                    fix_outcome=OUTCOME_NOT_RUN,
                    output_path="-",
                    actions=["NON ANALIZZATO"],
                )
            )
        return rows

    def _set_input_paths(self, paths: list[Path]) -> None:
        valid = [p for p in paths if p.exists()]
        if not valid:
            self._append_log("Input non valido")
            return
        if self._temp_input_dir and self._temp_input_dir.exists():
            shutil.rmtree(self._temp_input_dir, ignore_errors=True)
            self._temp_input_dir = None

        if len(valid) == 1:
            self.input_path = valid[0]
        else:
            tmp = Path(tempfile.mkdtemp(prefix="gdlex_multi_"))
            for src in valid:
                if src.is_file():
                    shutil.copy2(src, tmp / src.name)
            self._temp_input_dir = tmp
            self.input_path = tmp

        self.rows = self._collect_preview_rows(valid)
        self.last_summary = None
        self.last_output = None
        self.report_synthetic.clear()
        self.log.clear()
        self._refresh_model()
        selected_txt = str(self.input_path)
        self.details.setPlainText(f"Input selezionato: {selected_txt}")
        self.settings.setValue("last_input", selected_txt)
        self.btn_analyze.setEnabled(True)
        self.btn_sanitize.setEnabled(False)
        self._append_log(f"Drop handled: Input selezionato: {selected_txt}")

    def _ensure_input(self) -> bool:
        if self.input_path:
            return True
        self.choose_folder()
        return self.input_path is not None

    def run_analyze(self) -> None:
        if not self._ensure_input():
            return
        summary = analyze(self.input_path, self.profile)
        self.last_summary = summary
        self.rows = [
            RowState(
                source_path=str(item.source),
                original=item.source.name,
                file_type=item.file_type,
                status=item.status,
                issues=list(item.issues),
                new_name=item.suggested_name or item.source.name,
                fix_outcome=OUTCOME_NOT_RUN,
                output_path="-",
                actions=[],
            )
            for item in summary.files
        ]
        self._refresh_model()
        self.btn_sanitize.setEnabled(True)
        self._append_log("Analisi completata")
        for path, reason in summary.excluded_paths:
            self._append_log(f"Escluso da analisi ({reason}): {path}")

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
            create_backup=self.create_backup,
        )
        self.last_output = output
        self.last_summary = summary
        # aggiorna rows senza svuotare tabella
        mapping = {r.source_path: r for r in self.rows}
        for item in summary.files:
            row = mapping.get(str(item.source))
            if row is None:
                row = RowState(source_path=str(item.source), original=item.source.name, file_type=item.file_type, status=item.status)
                self.rows.append(row)
            row.source_path = str(item.source)
            row.status = item.status
            row.issues = list(item.issues)
            row.new_name = item.suggested_name or item.source.name
            row.fix_outcome = item.correction_outcome
            row.output_path = str(item.output_path) if item.output_path else "-"
            row.actions = list(item.correction_actions)

        self._refresh_model()
        self._append_log(f"Correzione completata: {output}")
        for item in summary.files:
            self._append_log(f"{item.source.name}: {item.correction_outcome} -> {item.output_path or '-'}")

    def _issue_tooltip(self, issues: list) -> str:
        if not issues:
            return "Nessuna criticità rilevata."
        blocks = []
        for issue in issues:
            cfg = PROBLEM_HELP.get(issue.code, {
                "title": issue.code,
                "description": issue.message,
                "fix": "Verifica manuale consigliata.",
            })
            blocks.append(
                f"<b>{cfg['title']}</b><br>{cfg['description']}<br>"
                f"<i>Perché nel deposito:</i> può influire su accettazione/leggibilità pratica.<br>"
                f"<i>Cosa fa l'autofix:</i> {cfg['fix']}<br>"
                f"<i>Cosa fare manualmente:</i> controllare il documento finale."
            )
        return "<hr>".join(blocks)

    def _display_outcome(self, outcome: str) -> str:
        if outcome in {OUTCOME_IMPOSSIBLE, OUTCOME_ERROR}:
            return "FALLITA"
        return outcome

    def _status_badge(self, status: str) -> str:
        return {"ok": "🟢 OK", "warning": "🟠 WARNING", "error": "🔴 ERROR", "non_analizzato": "⚪ NON ANALIZZATO"}.get(status, status.upper())

    def _refresh_model(self) -> None:
        self.model.removeRows(0, self.model.rowCount())
        ok = warn = err = 0
        corr = parz = fail = not_run = 0
        for row in self.rows:
            status_text = self._status_badge(row.status)
            if row.status == "ok":
                ok += 1
            elif row.status == "warning":
                warn += 1
            elif row.status == "error":
                err += 1

            if row.fix_outcome in {OUTCOME_FIXED, OUTCOME_OK}:
                corr += 1
            elif row.fix_outcome == OUTCOME_PARTIAL:
                parz += 1
            elif row.fix_outcome in {OUTCOME_IMPOSSIBLE, OUTCOME_ERROR}:
                fail += 1
            elif row.fix_outcome == OUTCOME_NOT_RUN:
                not_run += 1

            issues_txt = "; ".join(f"{i.level}:{i.code}" for i in row.issues) if row.issues else "-"
            actions_txt = " | ".join(row.actions) if row.actions else "-"

            items = [
                QStandardItem(row.original),
                QStandardItem(row.file_type),
                QStandardItem(status_text),
                QStandardItem(issues_txt),
                QStandardItem(row.new_name),
                QStandardItem(self._display_outcome(row.fix_outcome)),
                QStandardItem(row.output_path),
                QStandardItem(actions_txt),
            ]
            items[2].setToolTip(f"Stato finale: {status_text}. Significato deposito: verifica i warning/error prima invio.")
            items[3].setToolTip(self._issue_tooltip(row.issues))
            items[5].setToolTip(
                "CORRETTA: problemi risolti. PARZIALE: output creato ma restano warning/error. "
                "NON ESEGUITA: non è stata lanciata correzione. IMPOSSIBILE/ERRORE: intervento manuale necessario."
            )
            items[6].setToolTip(row.output_path)
            self.model.appendRow(items)

        if self.last_summary:
            self.report_synthetic.setPlainText(self._full_report_text(technical=False))
            self.log.setPlainText(self._full_report_text(technical=True))
        self.summary_label.setText(
            f"Riepilogo correzione: OK={ok} WARNING={warn} ERROR={err} | CORRETTA={corr} PARZIALE={parz} FALLITA={fail} NON ESEGUITA={not_run}"
        )

    def _on_table_double_clicked(self, index) -> None:
        if index.column() != 6:
            return
        path = self.model.item(index.row(), 6).text()
        if path and path != "-":
            QApplication.clipboard().setText(path)
            parent = str(Path(path).parent)
            QDesktopServices.openUrl(QUrl.fromLocalFile(parent))

    def _technical_dir(self) -> Path | None:
        return (self.last_output / ".gdlex") if self.last_output else None

    def open_output(self) -> None:
        if not self.last_output:
            QMessageBox.information(self, "Info", "Nessun output disponibile")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))

    def open_report_technical(self) -> None:
        tech = self._technical_dir()
        if not tech or not tech.exists():
            QMessageBox.information(self, "Info", "Nessun report tecnico disponibile")
            return
        target = tech / "REPORT.txt"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target if target.exists() else tech)))


    def _report_header(self) -> str:
        output = str(self.last_output) if self.last_output else "-"
        tech = self._technical_dir()
        tech_path = str(tech) if tech and tech.exists() else "-"
        return f"Output depositabile: {output}\nReport tecnico: {tech_path}\n\n"

    def _full_report_text(self, technical: bool = True) -> str:
        if not self.last_summary:
            return ""
        header = self._report_header()
        base = build_technical_report(self.last_summary) if technical else build_synthetic_report(self.last_summary)
        return header + base

    def copy_summary(self) -> None:
        QApplication.clipboard().setText(self.summary_label.text())
        self._append_log("Riepilogo copiato negli appunti")

    def copy_report(self) -> None:
        if not self.last_summary:
            return
        QApplication.clipboard().setText(self._full_report_text(technical=False) + "\n\n" + self._full_report_text(technical=True))
        self._append_log("Report copiato negli appunti")


    def _print_document(self, doc: QTextDocument, printer: QPrinter) -> None:
        if hasattr(doc, "print_"):
            doc.print_(printer)
        else:
            doc.print(printer)

    def print_report(self) -> None:
        if not self.last_summary:
            QMessageBox.information(self, "Info", "Nessun report disponibile")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        self._append_log(f"Print dialog accepted: {accepted}")
        if not accepted:
            self._append_log("Stampa report annullata")
            return
        try:
            doc = QTextDocument()
            doc.setPlainText(self._full_report_text(technical=True))
            self._print_document(doc, printer)
            self._append_log("Stampa report completata")
        except Exception as exc:  # pragma: no cover
            self._append_log(f"Stampa report fallita: {exc}")
            QMessageBox.warning(self, "Errore stampa", f"Stampa non riuscita:\n{exc}")

    def export_report_pdf(self) -> None:
        if not self.last_summary:
            QMessageBox.information(self, "Info", "Nessun report disponibile")
            return
        target, _ = QFileDialog.getSaveFileName(self, "Esporta report PDF", "report_tecnico.pdf", "PDF (*.pdf)")
        if not target:
            self._append_log("Export PDF annullato")
            return
        if not target.lower().endswith(".pdf"):
            target += ".pdf"
        self._append_log(f"Export PDF path: {target}")
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(target)
            doc = QTextDocument()
            doc.setPlainText(self._full_report_text(technical=True))
            self._print_document(doc, printer)
            if not Path(target).exists():
                raise RuntimeError("file PDF non creato")
            self._append_log(f"Report PDF esportato con successo: {target}")
            QMessageBox.information(self, "Export PDF", f"PDF creato correttamente:\n{target}")
        except Exception as exc:  # pragma: no cover
            self._append_log(f"Export PDF fallito: {exc}")
            QMessageBox.warning(self, "Errore export PDF", f"Export PDF non riuscito:\n{exc}")

    def show_settings(self) -> None:
        dialog = SettingsDialog(
            self,
            self.output_mode,
            self.custom_output_dir,
            self.smart_rename_enabled,
            self.max_filename_len,
            self.max_output_path_len,
            self.create_backup,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            mode, custom_dir, smart_enabled, max_filename_len, max_output_path_len, create_backup = dialog.values()
            self.output_mode = mode
            self.custom_output_dir = custom_dir
            self.smart_rename_enabled = smart_enabled
            self.max_filename_len = max_filename_len
            self.max_output_path_len = max_output_path_len
            self.create_backup = create_backup
            self.settings.setValue("output_mode", self.output_mode)
            self.settings.setValue("custom_output_dir", self.custom_output_dir)
            self.settings.setValue("smart_rename_enabled", self.smart_rename_enabled)
            self.settings.setValue("max_filename_len", self.max_filename_len)
            self.settings.setValue("max_output_path_len", self.max_output_path_len)
            self.settings.setValue("create_backup", self.create_backup)
            self._append_log("Impostazioni salvate")

    def reset(self) -> None:
        self.input_path = None
        self.last_output = None
        self.last_summary = None
        self.rows = []
        self.model.removeRows(0, self.model.rowCount())
        self.report_synthetic.clear()
        self.log.clear()
        self.details.clear()
        self.summary_label.setText("Riepilogo correzione: NON ESEGUITA")
        self.btn_sanitize.setEnabled(False)
        self._append_log("Stato resettato")

    def _restore_settings(self) -> None:
        geometry = self.settings.value("window_geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        splitter_sizes = self.settings.value("splitter_sizes")
        if splitter_sizes:
            self.splitter.setSizes([int(v) for v in splitter_sizes])
        else:
            self.splitter.setSizes([60, 20, 20])

        saved_input = self.settings.value("last_input")
        if saved_input and Path(saved_input).exists():
            self.input_path = Path(saved_input)

        saved_output = self.settings.value("last_output")
        if saved_output and Path(saved_output).exists():
            self.last_output = Path(saved_output)

        for index in range(self.model.columnCount()):
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
        self.settings.setValue("create_backup", self.create_backup)
        if self.input_path is not None:
            self.settings.setValue("last_input", str(self.input_path))
        if self.last_output is not None:
            self.settings.setValue("last_output", str(self.last_output))
        for index in range(self.model.columnCount()):
            self.settings.setValue(f"col_width_{index}", self.table.columnWidth(index))
        if self._temp_input_dir and self._temp_input_dir.exists():
            shutil.rmtree(self._temp_input_dir, ignore_errors=True)
        super().closeEvent(event)
