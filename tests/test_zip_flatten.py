import zipfile
from pathlib import Path

from core.sanitizer import _sanitize_zip


def test_zip_flatten_and_cleanup(tmp_path: Path):
    src = tmp_path / "in.zip"
    dst = tmp_path / "out.zip"
    with zipfile.ZipFile(src, "w") as zf:
        zf.writestr("folder/doc 1.pdf", b"%PDF-1.4\n%%EOF")
        zf.writestr("folder/Thumbs.db", b"x")

    profile = {
        "allowed_formats": ["pdf", "txt"],
        "warning_formats": [],
        "filename": {"max_length": 80},
    }
    actions, impossible = _sanitize_zip(src, dst, profile)

    with zipfile.ZipFile(dst, "r") as zf:
        names = zf.namelist()

    assert impossible is False
    assert "Thumbs.db" not in names
    assert len(names) == 1
    assert "/" not in names[0]
    assert any("Flatten" in a for a in actions)
