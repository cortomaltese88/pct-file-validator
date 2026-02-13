from core.sanitizer import _safe_target_name


def test_collision_suffixing():
    used = set()
    assert _safe_target_name("01_atto.pdf", used) == "01_atto.pdf"
    assert _safe_target_name("01_atto.pdf", used) == "01_atto_02.pdf"
