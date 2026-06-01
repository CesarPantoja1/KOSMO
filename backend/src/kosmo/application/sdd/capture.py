from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.ids import ProjectId, SpecId
from kosmo.contracts.sdd.repositories import ProjectRepository, SpecRepository
from kosmo.contracts.sdd.spec import SpecDocument, SpecPhase
from kosmo.domain.agents.spec_capture.service import capture
from kosmo.domain.sdd.id_generator import IdGenerator


class CaptureDiscoveryUseCase:
    def __init__(
        self,
        spec_repo: SpecRepository,
        project_repo: ProjectRepository,
        llm_client: LLMClient,
    ) -> None:
        self._spec_repo = spec_repo
        self._project_repo = project_repo
        self._llm_client = llm_client

    async def execute(
        self,
        project_id: ProjectId,
        description: str,
        optional_context: str = "",
    ) -> SpecDocument:
        from kosmo.contracts.sdd.discovery import RawIdea

        raw_idea = RawIdea(
            text=description,
            optional_context=optional_context,
        )

        discovery, document_tree = await capture(raw_idea, None, self._llm_client)

        spec = SpecDocument(
            id=SpecId(IdGenerator.generate("spec")),
            project_id=project_id,
            discovery=discovery,
            phase=SpecPhase.DESCUBRIMIENTO,
        )

        await self._spec_repo.add(spec)
        await self._project_repo.update_discovery_document(project_id, document_tree)
        return spec
