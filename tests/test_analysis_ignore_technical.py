from pathlib import Path

from core.sanitizer import analyze


def test_analysis_ignores_gdlex_and_conforme_dirs(tmp_path: Path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "doc.pdf").write_bytes(b"%PDF-1.4\n%%EOF")

    out = root / "foo_conforme"
    out.mkdir()
    (out / "REPORT.txt").write_text("x", encoding="utf-8")
    (out / "MANIFEST.csv").write_text("x", encoding="utf-8")

    gdlex = root / "bar" / ".gdlex"
    gdlex.mkdir(parents=True)
    (gdlex / "REPORT.json").write_text("{}", encoding="utf-8")

    profile = {
        "allowed_formats": ["pdf", "txt", "zip"],
        "warning_formats": [],
        "filename": {"max_length": 80},
    }

    summary = analyze(root, profile)
    names = [item.source.name for item in summary.files]
    assert names == ["doc.pdf"]
