from __future__ import annotations

import re
from datetime import UTC, datetime

from kosmo.contracts.sdd.document import AcceptanceCriterion, EARSPattern
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.ids import FeatureId, RequirementId

_req_header_re = re.compile(r"^###\s+(REQ-\d+\.\d+)\s+(.*)$", re.MULTILINE)
_req_pattern_re = re.compile(
    r"\*\*(Ubicuo|Basado en eventos|Determinado por estado"
    r"|Opcional|Comportamiento no deseado|Complejo)\*\*"
)
_ac_scenario_re = re.compile(r"\*\*Escenario:\s+(.+)\*\*")
_ac_given_re = re.compile(r"-\s+\*\*Dado\*\*\s+que\s+(.+)")
_ac_when_re = re.compile(r"-\s+\*\*Cuando\*\*\s+(.+)")
_ac_then_re = re.compile(r"-\s+\*\*Entonces\*\*\s+(.+)")

_req_count_re = re.compile(r"^###\s+REQ-\d+\.\d+", re.MULTILINE)

_PATTERN_MAP: dict[str, EARSPattern] = {
    "Ubicuo": EARSPattern.ubiquitous,
    "Basado en eventos": EARSPattern.event_driven,
    "Determinado por estado": EARSPattern.state_driven,
    "Opcional": EARSPattern.optional,
    "Comportamiento no deseado": EARSPattern.unwanted,
    "Complejo": EARSPattern.complex,
}


def parse_requirement_from_markdown(
    markdown: str,
    feature_id: FeatureId,
    feature_number: int,
    requirement_id: RequirementId,
) -> EARSRequirement | None:
    display_prefix = f"REQ-{feature_number}."
    blocks = markdown.split("### ")
    for block in blocks[1:]:
        first_line = block.split("\n")[0] if block else ""
        prefix = "### " if not block.startswith("REQ-") else ""
        header_match = _req_header_re.match(f"{prefix}{first_line}")
        if not header_match:
            full_header = block.split("\n")[0] if block else ""
            header_match = _req_header_re.match(f"### {full_header}")
        if not header_match:
            continue

        display_id = header_match.group(1)
        if not display_id.startswith(display_prefix):
            continue

        req_num_str = display_id.split(".")[-1]
        try:
            requirement_number = int(req_num_str)
        except ValueError:
            continue

        title = header_match.group(2).strip()
        pattern = _parse_pattern(block)
        statement = _parse_statement(block)
        acceptance_criteria = _parse_acceptance_criteria(block)

        return EARSRequirement(
            id=requirement_id,
            feature_id=feature_id,
            feature_number=feature_number,
            requirement_number=requirement_number,
            title=title,
            pattern=pattern,
            statement=statement,
            origin=_parse_origin(block),
            acceptance_criteria=acceptance_criteria,
            created_at=datetime.now(UTC),
        )

    return None


def parse_requirements_markdown(
    markdown: str,
    feature_id: FeatureId,
    feature_number: int,
) -> list[EARSRequirement]:
    display_prefix = f"REQ-{feature_number}."
    blocks = markdown.split("### ")
    results: list[EARSRequirement] = []
    for block in blocks[1:]:
        first_line = block.split("\n")[0] if block else ""
        prefix = "### " if not block.startswith("REQ-") else ""
        header_match = _req_header_re.match(f"{prefix}{first_line}")
        if not header_match:
            full_header = block.split("\n")[0] if block else ""
            header_match = _req_header_re.match(f"### {full_header}")
        if not header_match:
            continue

        display_id = header_match.group(1)
        if not display_id.startswith(display_prefix):
            continue

        req_num_str = display_id.split(".")[-1]
        try:
            requirement_number = int(req_num_str)
        except ValueError:
            continue

        from kosmo.domain.sdd.id_generator import IdGenerator

        title = header_match.group(2).strip()
        pattern = _parse_pattern(block)
        statement = _parse_statement(block)
        acceptance_criteria = _parse_acceptance_criteria(block)

        results.append(
            EARSRequirement(
                id=RequirementId(IdGenerator.generate("requirement")),
                feature_id=feature_id,
                feature_number=feature_number,
                requirement_number=requirement_number,
                title=title,
                pattern=pattern,
                statement=statement,
                origin=_parse_origin(block),
                acceptance_criteria=acceptance_criteria,
                created_at=datetime.now(UTC),
            )
        )

    return results


def count_requirements(markdown: str) -> int:
    return len(_req_count_re.findall(markdown))


def _parse_pattern(block: str) -> EARSPattern:
    pattern_match = _req_pattern_re.search(block)
    pattern_str = pattern_match.group(1) if pattern_match else "Ubicuo"
    return _PATTERN_MAP.get(pattern_str, EARSPattern.ubiquitous)


def _parse_statement(block: str) -> str:
    lines = block.split("\n")
    statement_lines: list[str] = []
    pattern_found = False
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("**") and ("Criterios" in stripped or "Escenario" in stripped):
            break
        if stripped.startswith("**") and not pattern_found:
            pattern_found = True
            continue
        if stripped and not stripped.startswith("**"):
            statement_lines.append(stripped)
    return " ".join(statement_lines).strip()


def _parse_acceptance_criteria(block: str) -> list[AcceptanceCriterion]:
    if "**Escenario:" not in block:
        return []
    ac_blocks = block.split("**Escenario:")
    criteria: list[AcceptanceCriterion] = []
    for ac_block in ac_blocks[1:]:
        scenario_match = _ac_scenario_re.search("**Escenario:" + ac_block)
        given_match = _ac_given_re.search(ac_block)
        when_match = _ac_when_re.search(ac_block)
        then_match = _ac_then_re.search(ac_block)
        if scenario_match:
            criteria.append(
                AcceptanceCriterion(
                    scenario=scenario_match.group(1).strip(),
                    given=given_match.group(1).strip() if given_match else "",
                    when=when_match.group(1).strip() if when_match else "",
                    then=then_match.group(1).strip() if then_match else "",
                )
            )
    return criteria


def _parse_origin(block: str) -> str:
    for line in block.split("\n"):
        stripped = line.strip()
        if stripped.startswith("**Origen:**"):
            return stripped.removeprefix("**Origen:**").strip()
    return ""
