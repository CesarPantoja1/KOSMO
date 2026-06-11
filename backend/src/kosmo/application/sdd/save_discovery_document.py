from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.memory.repositories import UserPreferenceRepository
from kosmo.contracts.sdd.document_repository import DocumentRepository
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository, SpecRepository


class SaveDiscoveryDocumentUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        spec_repo: SpecRepository,
        preference_repo: UserPreferenceRepository | None = None,
        llm_client: LLMClient | None = None,
        document_repo: DocumentRepository | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._spec_repo = spec_repo
        self._preference_repo = preference_repo
        self._llm_client = llm_client
        self._document_repo = document_repo

    async def execute(
        self,
        project_id: ProjectId,
        markdown: str,
        user_id: str = "",
    ) -> str:
        original = await self._document_repo.get_discovery_md(project_id) if self._document_repo else None

        if self._document_repo:
            try:
                await self._document_repo.save_discovery_md(project_id, markdown)
            except Exception:
                pass

        if (
            original
            and user_id
            and self._preference_repo
            and self._llm_client
            and original != markdown
        ):
            from kosmo.application.memory.learn_from_correction import (
                LearnFromCorrectionUseCase,
            )

            learn_uc = LearnFromCorrectionUseCase(
                preference_repo=self._preference_repo,
                llm_client=self._llm_client,
            )
            await learn_uc.execute(
                user_id=user_id,
                project_id=project_id,
                original_document={"markdown": original},
                corrected_document={"markdown": markdown},
                document_type="discovery",
            )

        return markdown
