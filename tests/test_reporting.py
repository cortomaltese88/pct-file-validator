from pathlib import Path

from core.models import AnalysisSummary, FileAnalysis, Issue
from core.reporting import build_synthetic_report, build_technical_report


def test_reporting_outputs_expected_sections(tmp_path: Path):
    sample = FileAnalysis(
        source=tmp_path / "Nota per Ufficiale Giudiziario_signed.pdf",
        file_type="pdf",
        status="warning",
        issues=[Issue(level="warning", code="filename_normalize", message="Nome file da normalizzare.")],
        correction_outcome="CORRETTA",
        correction_actions=["Rinominato file: Nota per Ufficiale Giudiziario_signed.pdf -> Nota_per_Ufficiale_Giudiziario_signed.pdf"],
        output_path=tmp_path / "Nota_per_Ufficiale_Giudiziario_signed.pdf",
    )
    summary = AnalysisSummary(files=[sample])

    synthetic = build_synthetic_report(summary)
    technical = build_technical_report(summary)

    assert "GD LEX - Report sintetico" in synthetic
    assert "WARNING | CORRETTA" in synthetic

    assert "GD LEX - Report tecnico" in technical
    assert "[ISSUE] filename_normalize" in technical
    assert "Rinominato file" in technical
    assert "Nota_per_Ufficiale_Giudiziario_signed.pdf" in technical
