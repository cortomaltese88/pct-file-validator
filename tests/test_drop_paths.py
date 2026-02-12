from pathlib import Path

import pytest

main_window = pytest.importorskip('gui.main_window', exc_type=ImportError)
paths_from_drop_urls = main_window.paths_from_drop_urls


def test_paths_from_drop_urls_filters_empty():
    paths = paths_from_drop_urls(["", "/tmp/a.pdf", "/tmp/b.zip"])
    assert paths == [Path('/tmp/a.pdf'), Path('/tmp/b.zip')]
