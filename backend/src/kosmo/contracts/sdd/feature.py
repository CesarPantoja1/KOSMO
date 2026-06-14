from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.sdd.document import FeatureStatus, RichTextDocument
from kosmo.contracts.sdd.ids import FeatureId


@dataclass(frozen=True)
class Feature:
    id: FeatureId
    number: int
    title: str
    slug: str
    description: str
    status: FeatureStatus = FeatureStatus.borrador
    rationale: str = ""
    inferred_from: list[str] = field(default_factory=list)
    requirements_document: RichTextDocument | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def display_id(self) -> str:
        return f"C{self.number:02d}"
