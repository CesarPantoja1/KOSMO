from typing import Protocol, runtime_checkable

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.sdd.ids import ProjectId


@runtime_checkable
class UserPreferenceRepository(Protocol):
    async def add(self, preference: UserPreference) -> None: ...
    async def get_by_user(
        self,
        user_id: str,
        project_id: ProjectId | None = None,
        document_type: str | None = None,
        limit: int = 20,
    ) -> list[UserPreference]: ...
    async def increment_usage(self, preference_ids: list[str]) -> None: ...
    async def delete(self, preference_id: str) -> None: ...
    async def update_confidence(self, preference_id: str, delta: float) -> None: ...
    async def delete_expired(self, threshold_confidence: float = 0.1) -> int: ...
