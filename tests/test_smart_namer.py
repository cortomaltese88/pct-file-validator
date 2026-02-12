from pathlib import Path

from core.smart_namer import classify_filename, detect_uuid_like, ensure_unique, smart_rename


def test_detect_uuid_like_true():
    assert detect_uuid_like("file_123e4567-e89b-12d3-a456-426614174000.pdf") is True


def test_detect_uuid_like_long_random_true():
    assert detect_uuid_like("AB12CD34EF56GH78IJ90KL12MN34OP56.pdf") is True


def test_classify_filename_pagopa():
    assert classify_filename("ricevuta_pagopa_123.pdf") == "Ricevuta_PagoPA"


def test_classify_filename_pec_keeps_meaningful_tokens():
    out = classify_filename("Indirizzo pec IPSO EDILE - Inipec.pdf")
    assert out == "PEC_INDIRIZZO_IPSO_EDILE_INIPEC"


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


def test_smart_rename_pagopa_uuid_like_human_name():
    opts = {"enabled": True, "max_filename_len": 80, "max_output_path_len": 180}
    name = "pagopa-ricevuta-123e4567-e89b-12d3-a456-426614174000.pdf"
    candidate, reasons = smart_rename(name, ".pdf", opts, {"output_dir": Path("/tmp")})
    assert candidate == "Ricevuta_PagoPA.pdf"
    assert "uuid_or_random_pattern" in reasons


def test_smart_rename_distinguishes_pec_subjects():
    opts = {"enabled": True, "max_filename_len": 140, "max_output_path_len": 200}
    a, _ = smart_rename("Indirizzo pec IPSO EDILE - Inipec.pdf", ".pdf", opts, {"output_dir": Path("/tmp")})
    b, _ = smart_rename("Indirizzo pec UNICREDIT SPA - Inipec.pdf", ".pdf", opts, {"output_dir": Path("/tmp")})
    assert a.startswith("PEC_INDIRIZZO_IPSO_EDILE_INIPEC")
    assert b.startswith("PEC_INDIRIZZO_UNICREDIT_INIPEC")
    assert a != b
