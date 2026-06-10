from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.memory.repositories import UserPreferenceRepository
from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.agents.learning.nodes import (
    conflict_resolver,
    delta_extractor,
    preference_store,
    rule_inferencer,
)


class LearnFromCorrectionUseCase:
    def __init__(
        self,
        preference_repo: UserPreferenceRepository,
        llm_client: LLMClient,
    ) -> None:
        self._preference_repo = preference_repo
        self._llm_client = llm_client

    async def execute(
        self,
        user_id: str,
        project_id: ProjectId,
        original_document: dict,
        corrected_document: dict,
        document_type: str,
    ) -> list[UserPreference]:
        delta = delta_extractor(original_document, corrected_document)
        if delta["added_lines"] == 0 and delta["removed_lines"] == 0:
            return []

        rules = await rule_inferencer(delta, document_type, self._llm_client)
        if not rules:
            return []

        resolved = await conflict_resolver(rules, user_id, project_id, self._preference_repo)
        unique_rules = [r for r in resolved if not r.get("duplicate")]
        if not unique_rules:
            return []

        return await preference_store(
            unique_rules, user_id, project_id, document_type, self._preference_repo
        )
