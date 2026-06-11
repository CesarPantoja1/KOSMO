from typing import Protocol, runtime_checkable

from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.requirements_document import RequirementsDocument


@runtime_checkable
class DocumentRepository(Protocol):
    async def save_discovery_md(self, project_id: ProjectId, markdown: str) -> None: ...

    async def get_discovery_md(self, project_id: ProjectId) -> str | None: ...

    async def save_clean_requirements(
        self, feature_id: FeatureId, requirements: RequirementsDocument
    ) -> None: ...

    async def get_clean_requirements(
        self, feature_id: FeatureId
    ) -> RequirementsDocument | None: ...
