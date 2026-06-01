"""DTOs Pydantic para operaciones de descubrimiento con documento enriquecido."""

from typing import Any

from pydantic import BaseModel

from kosmo.contracts.sdd.document import SectionHeading


class DiscoveryDocumentRequest(BaseModel):
    document: dict[str, Any]


class DiscoveryDocumentResponse(BaseModel):
    document: dict[str, Any]
    sections: list[SectionHeading]
    updated_at: str
