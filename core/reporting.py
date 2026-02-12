from __future__ import annotations

from core.models import AnalysisSummary


def build_synthetic_report(summary: AnalysisSummary) -> str:
    lines: list[str] = ["GD LEX - Report sintetico", "=" * 32]
    for item in summary.files:
        lines.append(f"{item.source.name}: {item.status.upper()} | {item.correction_outcome}")
    return "\n".join(lines)


def build_technical_report(summary: AnalysisSummary) -> str:
    lines: list[str] = ["GD LEX - Report tecnico", "=" * 32]
    for item in summary.files:
        lines.append(f"{item.source.name}")
        lines.append(f"  Stato: {item.status.upper()} | Esito: {item.correction_outcome}")
        if item.output_path:
            lines.append(f"  Output: {item.output_path}")
        for issue in item.issues:
            lines.append(f"  [ISSUE] {issue.code}: {issue.message}")
        for action in item.correction_actions:
            lines.append(f"  - {action}")
        lines.append("")
    return "\n".join(lines)
