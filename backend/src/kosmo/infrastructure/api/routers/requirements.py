from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.domain.sdd.document_converters import markdown_to_document

router = APIRouter(tags=["requirements"])


class GenerateRequirementsRequest(BaseModel):
    project_id: str


class SaveRequirementsRequest(BaseModel):
    project_id: str
    markdown: str


@router.post("/api/v1/features/{feature_id}/requirements/generate")
async def generate_requirements(
    feature_id: str,
    body: GenerateRequirementsRequest,
    request: Request,
) -> dict:
    uc = request.app.state.pipeline_components.generate_ears_uc
    output = await uc.execute(
        project_id=ProjectId(body.project_id),
        feature_id=FeatureId(feature_id),
    )
    requirements_data = []
    for req in output.requirements:
        requirements_data.append(
            {
                "id": str(req.id),
                "display_id": req.display_id,
                "feature_id": str(req.feature_id),
                "feature_number": req.feature_number,
                "requirement_number": req.requirement_number,
                "pattern": req.pattern.value,
                "trigger": req.trigger,
                "system": req.system,
                "response": req.response,
                "source_statement": req.source_statement,
                "rationale": req.rationale,
                "traceability": req.traceability,
                "acceptance_criteria": [
                    {"given": ac.given, "when": ac.when, "then": ac.then}
                    for ac in req.acceptance_criteria
                ],
            }
        )
    return {
        "feature_id": str(output.feature_id),
        "feature_number": output.feature_number,
        "requirements": requirements_data,
        "requirements_markdown": output.requirements_markdown,
        "validation": {
            "is_valid": output.validation_result.is_valid,
            "errors": output.validation_result.errors,
            "warnings": output.validation_result.warnings,
        },
        "metadata": {
            "llm_calls": output.generation_metadata.llm_calls,
            "retry_count": output.generation_metadata.retry_count,
            "model_used": output.generation_metadata.model_used,
        },
    }


@router.put("/api/v1/features/{feature_id}/requirements")
async def save_requirements(
    feature_id: str,
    body: SaveRequirementsRequest,
    request: Request,
) -> dict:
    uc = request.app.state.pipeline_components.save_requirements_uc
    doc = markdown_to_document(body.markdown)
    await uc.execute(
        project_id=ProjectId(body.project_id),
        feature_id=FeatureId(feature_id),
        document=doc,
    )
    return {"feature_id": feature_id, "message": "ok"}
