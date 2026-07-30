from __future__ import annotations


def apply_change_diff(markdown: str, *, before: str, after: str) -> str | None:
    if not before.strip():
        if after.strip():
            return f"{markdown}\n\n{after}"
        return markdown

    if before in markdown:
        return markdown.replace(before, after, 1)

    return None
