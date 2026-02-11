import json
from pathlib import Path

from core.sanitizer import sanitize


def test_manifest_created(tmp_path: Path):
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
    manifest_path = output / "manifest.json"
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(payload["files"]) == 1
