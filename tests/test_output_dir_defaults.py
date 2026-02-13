from pathlib import Path

from core.sanitizer import resolve_output_dir


def test_output_dir_default_sibling_for_directory(tmp_path: Path):
    input_dir = tmp_path / "pratica"
    input_dir.mkdir()
    assert resolve_output_dir(input_dir) == tmp_path / "pratica_conforme"


def test_output_dir_default_sibling_for_file(tmp_path: Path):
    input_file = tmp_path / "atto.pdf"
    input_file.write_text("x", encoding="utf-8")
    assert resolve_output_dir(input_file) == tmp_path / "atto_conforme"
