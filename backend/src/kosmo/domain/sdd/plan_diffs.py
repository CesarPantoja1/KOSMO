from __future__ import annotations

import re

_section_header_re = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def apply_change_diff(markdown: str, *, before: str, after: str, section: str | None = None) -> str | None:
    if not before.strip():
        if after.strip():
            if section:
                _sec, _start, _sec_end = find_section(markdown, section)
                if _sec is not None:
                    return _insert_in_section(markdown, _start, _sec_end, after)
            return f"{markdown}\n\n{after}"
        return markdown

    if section:
        return _apply_section_diff(markdown, before, after, section)

    return _try_replace(markdown, before, after)


def _try_replace(text: str, before: str, after: str) -> str | None:
    if before in text:
        return text.replace(before, after, 1)
    if before.strip() in text:
        return text.replace(before.strip(), after.strip(), 1)
    normalized_before = collapse_whitespace(before)
    normalized_text = collapse_whitespace(text)
    if normalized_before in normalized_text:
        return _apply_normalized_replace(text, before, after)
    if after in text:
        return text
    return None


def _apply_section_diff(markdown: str, before: str, after: str, section: str) -> str | None:
    section_text, start, end = find_section(markdown, section)
    if section_text is not None:
        result = _try_replace(section_text, before, after)
        if result is not None and result != section_text:
            return markdown[:start] + result + markdown[end:]
        if result is not None:
            return markdown

    return _try_replace(markdown, before, after)


def find_section(markdown: str, section: str) -> tuple[str | None, int, int]:
    matches = list(_section_header_re.finditer(markdown))
    normalized_query = _normalize(section)

    for i, m in enumerate(matches):
        heading_text = m.group(2)
        if _normalize(heading_text) == normalized_query:
            return _extract_section(markdown, matches, i)
        if normalized_query in _normalize(heading_text):
            return _extract_section(markdown, matches, i)

    return None, 0, 0


def _extract_section(markdown: str, matches: list[re.Match[str]], idx: int) -> tuple[str, int, int]:
    start = matches[idx].start()
    end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
    return markdown[start:end], start, end


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


_FUTURE_HINTS = (
    "futur",
    "no contempl",
    "pendiente",
    "proxim",
    "roadmap",
    "potencial",
    "fuera de alcance",
    "no incluido",
    "a considerar",
)


def _insert_in_section(markdown: str, sec_start: int, sec_end: int, after: str) -> str:
    section_md = markdown[sec_start:sec_end]
    headings = list(_section_header_re.finditer(section_md))
    if len(headings) >= 3:
        insert_pos = _find_future_boundary(section_md, headings)
        if insert_pos is None:
            insert_pos = section_md.rfind("\n\n", 0, headings[-1].start())
            if insert_pos < 0:
                insert_pos = headings[-1].start()
        head = markdown[sec_start : sec_start + insert_pos].rstrip()
        tail = markdown[sec_start + insert_pos : sec_end].lstrip("\n")
        return markdown[:sec_start] + head + "\n" + after.strip() + "\n\n" + tail + markdown[sec_end:]
    head = markdown[:sec_end].rstrip()
    tail = markdown[sec_end:].lstrip("\n")
    return head + "\n" + after.strip() + "\n\n" + tail


def _find_future_boundary(section_md: str, headings: list[re.Match[str]]) -> int | None:
    for m in headings[1:]:
        heading_text = _normalize(m.group(2))
        if any(hint in heading_text for hint in _FUTURE_HINTS):
            boundary = section_md.rfind("\n\n", 0, m.start())
            return boundary if boundary >= 0 else m.start()
    return None


def _apply_normalized_replace(text: str, before: str, after: str) -> str | None:
    lines = text.splitlines(keepends=True)
    before_lines = before.strip().splitlines()
    after_lines = after.strip().splitlines()

    for i in range(len(lines) - len(before_lines) + 1):
        window = [lines[j].strip() for j in range(i, i + len(before_lines))]
        if window == [bl.strip() for bl in before_lines]:
            result_lines = list(lines)
            result_lines[i : i + len(before_lines)] = [al + "\n" for al in after_lines]
            return "".join(result_lines)

    return None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()
