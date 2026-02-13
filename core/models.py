from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Issue:
    level: str  # info | warning | error
    code: str
    message: str


@dataclass(slots=True)
class FileAnalysis:
    source: Path
    file_type: str
    status: str  # ok | warning | error
    issues: list[Issue] = field(default_factory=list)
    suggested_name: str | None = None
    sha256: str | None = None
    correction_outcome: str = "NON ESEGUITA"
    correction_actions: list[str] = field(default_factory=list)
    output_path: Path | None = None


@dataclass(slots=True)
class AnalysisSummary:
    files: list[FileAnalysis]
    excluded_paths: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(f.status == "error" for f in self.files)

    def to_dict(self) -> dict:
        payload: dict[str, list[dict]] = {"files": []}
        for item in self.files:
            payload["files"].append(
                {
                    "source": str(item.source),
                    "file_type": item.file_type,
                    "status": item.status,
                    "issues": [{"level": issue.level, "code": issue.code, "message": issue.message} for issue in item.issues],
                    "suggested_name": item.suggested_name,
                    "sha256": item.sha256,
                    "correction_outcome": item.correction_outcome,
                    "correction_actions": item.correction_actions,
                    "output_path": str(item.output_path) if item.output_path else None,
                }
            )
        return payload
