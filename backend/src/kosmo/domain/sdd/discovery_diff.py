from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ChangeType(StrEnum):
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


class ChangeClass(StrEnum):
    COSMETIC = "cosmetic"
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"
    BUSINESS_RULE = "business_rule"


@dataclass(frozen=True)
class SectionChange:
    section: str
    change_type: ChangeType
    change_class: ChangeClass
    before: str = ""
    after: str = ""


def _extract_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(markdown))
    if not matches:
        sections[""] = markdown
        return sections

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        content = markdown[start:end].strip()
        if content:
            sections[match.group(1).strip()] = content

    return sections


def _normalize_for_cosmetic(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _is_cosmetic_change(before: str, after: str) -> bool:
    return _normalize_for_cosmetic(before) == _normalize_for_cosmetic(after)


_BUSINESS_TERMS = frozenset(
    {
        "precio",
        "costo",
        "moneda",
        "peso",
        "unidad",
        "plazo",
        "porcentaje",
        "impuesto",
        "descuento",
        "garantia",
        "reembolso",
        "suscripcion",
        "factura",
        "presupuesto",
        "comision",
    }
)


def _detect_business_terms(text: str) -> set[str]:
    words = set(re.findall(r"\b[a-záéíóúñ]+\b", text.lower()))
    return words & _BUSINESS_TERMS


def _classify_change(before: str, after: str) -> ChangeClass:
    if not before:
        return ChangeClass.STRUCTURAL
    if not after:
        return ChangeClass.STRUCTURAL
    if _is_cosmetic_change(before, after):
        return ChangeClass.COSMETIC
    terms_before = _detect_business_terms(before)
    terms_after = _detect_business_terms(after)
    if terms_before != terms_after:
        return ChangeClass.BUSINESS_RULE
    return ChangeClass.SEMANTIC


def diff_discovery_versions(previous: str, current: str) -> list[SectionChange]:
    prev_sections = _extract_sections(previous)
    curr_sections = _extract_sections(current)
    changes: list[SectionChange] = []

    all_headings = sorted(set(prev_sections.keys()) | set(curr_sections.keys()), key=str)
    for heading in all_headings:
        prev_content = prev_sections.get(heading, "")
        curr_content = curr_sections.get(heading, "")

        if heading not in prev_sections:
            changes.append(
                SectionChange(
                    section=heading,
                    change_type=ChangeType.ADDED,
                    change_class=ChangeClass.STRUCTURAL,
                    before="",
                    after=curr_content,
                )
            )
        elif heading not in curr_sections:
            changes.append(
                SectionChange(
                    section=heading,
                    change_type=ChangeType.REMOVED,
                    change_class=ChangeClass.STRUCTURAL,
                    before=prev_content,
                    after="",
                )
            )
        elif prev_content != curr_content:
            change_class = _classify_change(prev_content, curr_content)
            changes.append(
                SectionChange(
                    section=heading,
                    change_type=ChangeType.MODIFIED,
                    change_class=change_class,
                    before=prev_content,
                    after=curr_content,
                )
            )

    return changes


def diff_from_plan_changes(plan_changes: list[object]) -> list[SectionChange]:
    changes: list[SectionChange] = []
    for c in plan_changes:
        section = getattr(c, "section", "") or ""
        before = getattr(getattr(c, "diff", None), "before", "") or ""
        after = getattr(getattr(c, "diff", None), "after", "") or ""
        change_class = _classify_change(before, after)
        change_type = ChangeType.ADDED if not before else (ChangeType.REMOVED if not after else ChangeType.MODIFIED)
        changes.append(
            SectionChange(
                section=section,
                change_type=change_type,
                change_class=change_class,
                before=before,
                after=after,
            )
        )
    return changes
