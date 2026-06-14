from __future__ import annotations

from typing import Protocol

from kosmo.contracts.memory.user_preference import UserPreference


class UserPreferenceRepository(Protocol):
    async def get_by_user(self, user_id: str) -> list[UserPreference]: ...
    async def save(self, preference: UserPreference) -> UserPreference: ...
    async def delete(self, preference_id: str) -> None: ...
