from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.sdd.ids import ProjectId, UserId


@dataclass(frozen=True)
class Project:
    id: ProjectId
    name: str
    slug: str
    description: str
    owner_id: UserId
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
