from kosmo.contracts.memory.repositories import UserPreferenceRepository
from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.agents.memory_agent.nodes import injection_preparer


class InjectPreferencesUseCase:
    def __init__(self, preference_repo: UserPreferenceRepository) -> None:
        self._preference_repo = preference_repo

    async def execute(
        self,
        user_id: str,
        project_id: ProjectId | None = None,
        document_type: str | None = None,
    ) -> tuple[list[UserPreference], str]:
        prefs = await self._preference_repo.get_by_user(
            user_id=user_id,
            project_id=project_id,
            document_type=document_type,
            limit=20,
        )

        prompt_section = injection_preparer(prefs)
        return prefs, prompt_section
