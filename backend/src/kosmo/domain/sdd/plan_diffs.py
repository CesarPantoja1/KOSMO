from __future__ import annotations

import re

_section_header_re = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)


def apply_change_diff(markdown: str, *, before: str, after: str, section: str | None = None) -> str | None:
    if not before.strip():
        if after.strip():
            return f"{markdown}\n\n{after}"
        return markdown

    if section:
        return _apply_section_diff(markdown, before, after, section)

    if before in markdown:
        return markdown.replace(before, after, 1)

    if after in markdown:
        return markdown

    return None


def _apply_section_diff(markdown: str, before: str, after: str, section: str) -> str | None:
    section_text, start, end = _find_section(markdown, section)
    if section_text is None:
        if before in markdown:
            return markdown.replace(before, after, 1)
        if after in markdown:
            return markdown
        return None

    if before in section_text:
        new_section = section_text.replace(before, after, 1)
        return markdown[:start] + new_section + markdown[end:]

    if after in section_text:
        return markdown

    return None


def _find_section(markdown: str, section: str) -> tuple[str | None, int, int]:
    """Busca una sección por nombre y retorna (texto_de_sección, inicio, fin)."""
    matches = list(_section_header_re.finditer(markdown))
    target_idx: int | None = None
    normalized = _normalize(section)

    for i, m in enumerate(matches):
        if normalized in _normalize(m.group(2)):
            target_idx = i
            break

    if target_idx is None:
        return None, 0, 0

    start = matches[target_idx].start()
    end = matches[target_idx + 1].start() if target_idx + 1 < len(matches) else len(markdown)

    return markdown[start:end], start, end


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()
