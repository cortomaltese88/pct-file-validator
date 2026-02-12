from pathlib import Path

from core.sanitizer import OUTCOME_FIXED, OUTCOME_IMPOSSIBLE, sanitize


def test_sanitize_processes_all_files(tmp_path: Path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "atto uno.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
    (root / "video.mp4").write_bytes(b"fake")

    profile = {
        "allowed_formats": ["pdf", "zip", "txt"],
        "warning_formats": ["png"],
        "filename": {"max_length": 80},
    }

    output, summary = sanitize(root, profile)
    assert output.exists()
    by_name = {item.source.name: item for item in summary.files}

    assert by_name["atto uno.pdf"].correction_outcome in {OUTCOME_FIXED, "OK"}
    assert by_name["video.mp4"].correction_outcome == OUTCOME_IMPOSSIBLE
