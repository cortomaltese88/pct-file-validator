from pathlib import Path

from core.smart_namer import detect_uuid_like, ensure_unique, smart_rename


def test_detect_uuid_like_true():
    assert detect_uuid_like("file_123e4567-e89b-12d3-a456-426614174000.pdf") is True


def test_detect_uuid_like_long_random_true():
    assert detect_uuid_like("AB12CD34EF56GH78IJ90KL12MN34OP56.pdf") is True


def test_ensure_unique_sequence():
    used = set()
    assert ensure_unique(used, "Atto_Precetto.pdf") == "Atto_Precetto.pdf"
    assert ensure_unique(used, "Atto_Precetto.pdf") == "Atto_Precetto_02.pdf"


def test_smart_rename_path_trim():
    long = "X" * 120 + ".pdf"
    opts = {"enabled": True, "max_filename_len": 60, "max_output_path_len": 100}
    candidate, reasons = smart_rename(long, ".pdf", opts, {"output_dir": Path("/tmp/" + "a" * 40)})
    assert len(candidate) <= 60
    assert "path_too_long_mitigated" in reasons


def test_no_signed_signed_regression():
    opts = {"enabled": True, "max_filename_len": 60, "max_output_path_len": 180}
    candidate, _ = smart_rename("atto_signed.pdf", ".pdf", opts, {"output_dir": Path("/tmp")})
    assert "_signed_signed" not in candidate


def test_smart_rename_preserves_words_no_semantic_substitution():
    opts = {"enabled": True, "max_filename_len": 120, "max_output_path_len": 180}
    candidate, _ = smart_rename(
        "Nota per Ufficiale Giudiziario_signed.pdf",
        ".pdf",
        opts,
        {"output_dir": Path("/tmp")},
    )
    assert candidate == "Nota_per_Ufficiale_Giudiziario_signed.pdf"
    assert "Notifica" not in candidate
