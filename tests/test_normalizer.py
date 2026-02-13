from core.normalizer import sanitize_filename


def test_sanitize_filename_basic():
    assert sanitize_filename("Atto di citazione àèé.pdf") == "Atto_di_citazione_aee.pdf"


def test_sanitize_filename_trim():
    name = "x" * 200 + ".pdf"
    assert len(sanitize_filename(name, max_len=80)) <= 80


def test_sanitize_filename_preserves_words_only_technical_changes():
    src = "Nota per Ufficiale Giudiziario_signed.pdf"
    out = sanitize_filename(src)
    assert out == "Nota_per_Ufficiale_Giudiziario_signed.pdf"
    assert "Notifica" not in out


def test_sanitize_filename_removes_forbidden_chars_without_semantic_rewrite():
    src = "Nota: ufficiale*giudiziario?.pdf"
    out = sanitize_filename(src)
    assert out == "Nota_ufficiale_giudiziario.pdf"
