from __future__ import annotations

import re
import unicodedata
from pathlib import Path

ACCENT_MAP = str.maketrans(
    {
        "à": "a",
        "è": "e",
        "é": "e",
        "ì": "i",
        "ò": "o",
        "ù": "u",
        "À": "A",
        "È": "E",
        "É": "E",
        "Ì": "I",
        "Ò": "O",
        "Ù": "U",
    }
)

VALID_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def strip_accents(text: str) -> str:
    mapped = text.translate(ACCENT_MAP)
    decomposed = unicodedata.normalize("NFKD", mapped)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def sanitize_filename(name: str, max_len: int = 80) -> str:
    path = Path(name)
    extension = path.suffix
    stem = path.stem
    cleaned = strip_accents(stem)
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-") or "file"

    budget = max_len - len(extension)
    if budget < 1:
        budget = 1
    cleaned = cleaned[:budget]
    return f"{cleaned}{extension}"


def is_filename_valid(name: str, max_len: int = 80) -> bool:
    if len(name) > max_len:
        return False
    return bool(VALID_FILENAME_RE.match(name))
