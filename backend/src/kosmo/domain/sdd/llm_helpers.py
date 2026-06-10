import json
import re
from typing import Any

_MARKDOWN_BOLD = re.compile(r"\*\*(.*?)\*\*")
_MARKDOWN_ITALIC = re.compile(r"\*(.*?)\*")
_MARKDOWN_CODE = re.compile(r"`(.*?)`")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MARKDOWN_LIST_BULLET = re.compile(r"^[\s]*[-*+]\s+", re.MULTILINE)
_FIELD_LABEL = re.compile(r"^\*\*(Título|Descripción|Titulo|Descripcion):\*\*\s*", re.IGNORECASE)


def strip_markdown_formatting(text: str) -> str:
    if not text:
        return text

    cleaned = _MARKDOWN_BOLD.sub(r"\1", text)
    cleaned = _MARKDOWN_ITALIC.sub(r"\1", cleaned)
    cleaned = _MARKDOWN_CODE.sub(r"\1", cleaned)
    cleaned = _MARKDOWN_HEADING.sub("", cleaned)
    cleaned = _MARKDOWN_LIST_BULLET.sub("", cleaned)
    cleaned = _FIELD_LABEL.sub("", cleaned)
    cleaned = cleaned.replace("\\n", " ")
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned)

    return cleaned.strip()


def strip_llm_artifacts(text: str) -> str:
    if not text:
        return text

    cleaned = _FIELD_LABEL.sub("", text)
    cleaned = cleaned.replace("\\n", " ")

    return cleaned.strip()


def extract_json(text: str) -> Any:
    fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    match = fence_pattern.search(text)
    if match:
        clean = match.group(1).strip()
    else:
        first_brace = text.find("{")
        first_bracket = text.find("[")
        if first_brace == -1 and first_bracket == -1:
            return text.strip()

        if first_bracket != -1 and (first_bracket < first_brace or first_brace == -1):
            start = first_bracket
            opener = "["
            closer = "]"
        else:
            start = first_brace
            opener = "{"
            closer = "}"

        depth = 0
        end = start
        for i, ch in enumerate(text[start:], start):
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        clean = text[start:end]

    try:
        return json.loads(clean)
    except (json.JSONDecodeError, ValueError):
        return clean
