from core.normalizer import sanitize_filename


def test_sanitize_filename_basic():
    assert sanitize_filename("Atto di citazione àèé.pdf") == "Atto_di_citazione_aee.pdf"


def test_sanitize_filename_trim():
    name = "x" * 200 + ".pdf"
    assert len(sanitize_filename(name, max_len=80)) <= 80
