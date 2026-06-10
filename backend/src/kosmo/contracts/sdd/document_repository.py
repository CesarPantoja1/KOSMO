from typing import Protocol, runtime_checkable

from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.requirements_document import RequirementsDocument


@runtime_checkable
class DocumentRepository(Protocol):
    async def save_view(self, resource_type: str, resource_id: str, document: dict) -> None: ...

    async def get_view(self, resource_type: str, resource_id: str) -> dict | None: ...

    async def save_clean_discovery(
        self, project_id: ProjectId, discovery: DiscoveryDocument
    ) -> None: ...

    async def get_clean_discovery(self, project_id: ProjectId) -> DiscoveryDocument | None: ...

    async def save_clean_requirements(
        self, feature_id: FeatureId, requirements: RequirementsDocument
    ) -> None: ...

    async def get_clean_requirements(
        self, feature_id: FeatureId
    ) -> RequirementsDocument | None: ...

    async def sync_clean_from_view(
        self, resource_type: str, resource_id: str
    ) -> DiscoveryDocument | RequirementsDocument | None: ...
