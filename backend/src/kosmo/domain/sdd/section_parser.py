from __future__ import annotations

import re

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def section_spans(markdown: str) -> list[tuple[str, int, int]]:
    """Devuelve (titulo, inicio, fin) de cada seccion del markdown."""
    matches = list(_HEADING_RE.finditer(markdown))
    spans: list[tuple[str, int, int]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        spans.append((m.group(2), m.start(), end))
    return spans


def section_heading_preserved(original: str, rewritten: str) -> bool:
    """True si el primer heading del original sigue presente en la reescritura."""

    def _first_heading(text: str) -> str:
        m = _HEADING_RE.search(text)
        return re.sub(r"\s+", "", (m.group(2) if m else "")).lower()

    original_heading = _first_heading(original)
    if not original_heading:
        return True
    return original_heading in re.sub(r"\s+", "", rewritten).lower()
