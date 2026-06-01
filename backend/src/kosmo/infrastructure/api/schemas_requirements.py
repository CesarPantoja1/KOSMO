"""DTOs Pydantic para operaciones de requisitos con documento enriquecido."""

from typing import Any

from pydantic import BaseModel

from kosmo.contracts.sdd.document import SectionHeading


class RequirementsDocumentRequest(BaseModel):
    document: dict[str, Any]


class RequirementsDocumentResponse(BaseModel):
    document: dict[str, Any]
    sections: list[SectionHeading]
    feature_title: str
    feature_description: str
    updated_at: str
