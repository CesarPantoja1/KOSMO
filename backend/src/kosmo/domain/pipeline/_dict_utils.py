from __future__ import annotations

from typing import Any, cast


def dict_str_keys(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {}
    return {k: v for k, v in d.items() if isinstance(k, str)}  # type: ignore[reportUnknownVariableType]


def extract_requirements_list(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, dict):
        raw: object = content.get("requirements", [])  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if isinstance(raw, list):
            result: list[dict[str, Any]] = []
            for item in cast(list[object], raw):
                if isinstance(item, dict):
                    result.append(dict_str_keys(item))
            return result
    if isinstance(content, list):
        result: list[dict[str, Any]] = []
        for item in cast(list[object], content):
            if isinstance(item, dict):
                result.append(dict_str_keys(item))
        return result
    return []


def requirements_to_markdown(reqs: list[Any]) -> str:
    blocks: list[str] = []
    for r in reqs:
        if not (hasattr(r, "display_id") and hasattr(r, "statement")):
            continue

        title = getattr(r, "title", "")
        pattern_display = str(r.pattern) if hasattr(r, "pattern") else ""
        statement = r.statement.strip()
        display_id = r.display_id

        block = f"### {display_id} {title}\n\n"
        block += f"**{pattern_display}**\n\n"
        block += f"{statement}\n"

        if hasattr(r, "acceptance_criteria") and r.acceptance_criteria:
            block += "\n**Criterios de Aceptación**\n\n"
            for ac in r.acceptance_criteria:
                scenario = getattr(ac, "scenario", "")
                given_text = getattr(ac, "given", "")
                when_text = getattr(ac, "when", "")
                then_text = getattr(ac, "then", "")

                block += f"**Escenario: {scenario}**\n\n"
                block += f"- **Dado** que {given_text}\n"
                block += f"- **Cuando** {when_text}\n"
                block += f"- **Entonces** {then_text}\n\n"

        blocks.append(block.strip())

    return "\n\n---\n\n".join(blocks).strip()
