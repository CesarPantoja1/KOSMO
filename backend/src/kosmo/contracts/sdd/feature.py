from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.ids import FeatureId, ProjectId


@dataclass
class Feature:
    id: FeatureId
    project_id: ProjectId
    number: int
    title: str
    slug: str
    description: str
    rationale: str = ""
    inferred_from: list[str] = field(default_factory=list)
    requirements_document: RichTextDocument | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def display_id(self) -> str:
        return f"C{self.number:02d}"
