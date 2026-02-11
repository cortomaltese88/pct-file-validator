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


@dataclass(slots=True)
class AnalysisSummary:
    files: list[FileAnalysis]

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
                    "issues": [issue.__dict__ for issue in item.issues],
                    "suggested_name": item.suggested_name,
                    "sha256": item.sha256,
                }
            )
        return payload
