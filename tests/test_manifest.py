import json
from pathlib import Path

from core.sanitizer import sanitize


def test_reports_created_in_gdlex(tmp_path: Path):
    root = tmp_path / "fascicolo"
    root.mkdir()
    sample = root / "atto.pdf"
    sample.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

    profile = {
        "allowed_formats": ["pdf", "txt", "zip"],
        "warning_formats": [],
        "filename": {"max_length": 80},
    }
    output, _ = sanitize(root, profile)

    gdlex = output / ".gdlex"
    assert gdlex.exists()
    assert (gdlex / "REPORT.json").exists()
    assert (gdlex / "REPORT.txt").exists()
    assert (gdlex / "MANIFEST.csv").exists()

    assert not (output / "REPORT.json").exists()
    assert not (output / "REPORT.txt").exists()
    assert not (output / "MANIFEST.csv").exists()

    payload = json.loads((gdlex / "REPORT.json").read_text(encoding="utf-8"))
    assert len(payload["files"]) == 1
