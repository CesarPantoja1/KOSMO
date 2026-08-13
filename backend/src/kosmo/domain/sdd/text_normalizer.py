from __future__ import annotations

import re


def normalize_for_match(text: str) -> str:
    """Normaliza texto para comparaciones tolerantes a formato."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()
