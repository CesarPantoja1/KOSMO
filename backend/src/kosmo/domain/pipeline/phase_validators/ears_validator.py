from __future__ import annotations

from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.domain.sdd.output_guardrails import (
    auto_repair_technical_terms,
    detect_implementation_leaks,
)
from kosmo.domain.sdd.validators.ears_validator import (
    validate_ears_quality,
    validate_ears_syntax,
)


def validate_ears_syntax_wrapper(
    requirements: list[EARSRequirement],
) -> ValidationResult:
    return validate_ears_syntax(requirements)


def validate_ears_quality_wrapper(
    requirements: list[EARSRequirement],
) -> ValidationResult:
    return validate_ears_quality(requirements)


def detect_implementation_leaks_wrapper(
    requirements: list[EARSRequirement],
) -> ValidationResult:
    req_dicts = [
        {
            "id": req.display_id,
            "source_statement": req.source_statement,
            "response": req.response,
        }
        for req in requirements
    ]
    result = detect_implementation_leaks(req_dicts)
    return ValidationResult(
        is_valid=result.is_valid,
        errors=result.error_messages,
        warnings=[],
    )


def auto_repair_leaks(
    requirements: list[EARSRequirement],
) -> list[EARSRequirement]:
    repaired: list[EARSRequirement] = []
    for req in requirements:
        repaired_statement = auto_repair_technical_terms(req.source_statement)
        repaired_response = auto_repair_technical_terms(req.response)
        repaired_rationale = auto_repair_technical_terms(req.rationale)
        repaired.append(
            EARSRequirement(
                id=req.id,
                feature_id=req.feature_id,
                feature_number=req.feature_number,
                requirement_number=req.requirement_number,
                pattern=req.pattern,
                trigger=auto_repair_technical_terms(req.trigger),
                system=req.system,
                response=repaired_response,
                source_statement=repaired_statement,
                rationale=repaired_rationale,
                traceability=req.traceability,
                acceptance_criteria=req.acceptance_criteria,
                created_at=req.created_at,
            )
        )
    return repaired
