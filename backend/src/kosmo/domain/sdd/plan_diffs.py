from __future__ import annotations

import re

_section_header_re = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def apply_change_diff(markdown: str, *, before: str, after: str, section: str | None = None) -> str | None:
    if not before.strip():
        if after.strip():
            if section:
                _sec, _start, _sec_end = find_section(markdown, section)
                if _sec is not None:
                    return markdown[:_sec_end].rstrip() + "\n" + after.strip() + "\n\n" + markdown[_sec_end:].lstrip()
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
