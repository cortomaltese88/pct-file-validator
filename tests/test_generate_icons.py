from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

pytest.importorskip("PIL", exc_type=ImportError)

spec = spec_from_file_location("generate_icons", Path("tools/generate_icons.py"))
module = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
generate_icons = module.generate_icons


def test_generate_icons_outputs_files(tmp_path: Path):
    generated = generate_icons(tmp_path)
    assert generated["source_png"].exists()
    assert generated["png_256"].exists()
    assert generated["ico"].exists()
