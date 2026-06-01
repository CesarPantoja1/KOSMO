import json
import re


def extract_json(text: str) -> str:
    fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    match = fence_pattern.search(text)
    if match:
        return match.group(1).strip()

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

    return text[start:end]


def parse_model_response(text: str, model_class: type) -> object:
    clean = extract_json(text)
    try:
        return model_class.model_validate_json(clean)
    except Exception:
        data = json.loads(clean)
        return model_class.model_validate(data)
