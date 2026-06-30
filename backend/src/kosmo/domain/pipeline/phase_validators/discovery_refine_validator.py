from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.domain.sdd.output_guardrails import detect_technical_terms


def validate_business_level(doc: RichTextDocument) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    for node in doc.nodes:
        section_name = node.heading.text if node.heading else ""
        texts: list[str] = []
        if node.heading and node.heading.text:
            texts.append(node.heading.text)
        if node.content:
            texts.append(node.content)

        for text in texts:
            result = detect_technical_terms(text, section=section_name)
            if result.is_valid:
                continue
            for violation in result.violations:
                errors.append(
                    f"Termino tecnico prohibido '{violation.term}' encontrado "
                    f"en seccion '{violation.section}': {violation.context}"
                )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
