from pathlib import Path

from core.sanitizer import sanitize


def test_sanitize_collision_resolved_incrementally(tmp_path: Path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "ricevuta_pagopa_123e4567-e89b-12d3-a456-426614174000.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
    (root / "ricevuta_pagopa_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.pdf").write_bytes(b"%PDF-1.4\n%%EOF")

    profile = {
        "allowed_formats": ["pdf", "zip", "txt"],
        "warning_formats": [],
        "filename": {"max_length": 80},
    }

    out, summary = sanitize(root, profile, smart_opts={"enabled": True, "max_filename_len": 20, "max_output_path_len": 180})
    outputs = sorted([p.name for p in out.iterdir() if p.is_file()])
    assert len(outputs) == 2
    assert outputs[0] != outputs[1]
    assert any("_02" in name for name in outputs)
    assert all(item.correction_outcome in {"CORRETTA", "OK", "PARZIALE"} for item in summary.files)
