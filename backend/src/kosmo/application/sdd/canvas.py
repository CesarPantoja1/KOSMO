from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.domain_model import DomainModel
from kosmo.contracts.sdd.ids import SpecId
from kosmo.contracts.sdd.repositories import SpecRepository
from kosmo.contracts.sdd.spec import SpecDocument
from kosmo.domain.agents.canvas_sync.service import CanvasEdit, ChangeDelta, apply_canvas_edit


class SyncCanvasEditUseCase:
    def __init__(
        self,
        spec_repo: SpecRepository,
        llm_client: LLMClient,
    ) -> None:
        self._spec_repo = spec_repo
        self._llm_client = llm_client

    async def execute(self, spec_id: SpecId, edit: CanvasEdit) -> tuple[SpecDocument, ChangeDelta]:
        spec = await self._spec_repo.get(spec_id)
        if spec is None:
            raise Exception(f"Especificación no encontrada: {spec_id}")

        current_model = spec.design if spec.design else DomainModel()
        updated_model, delta = await apply_canvas_edit(
            edit=edit,
            current_model=current_model,
            llm_client=self._llm_client,
        )

        spec.design = updated_model
        await self._spec_repo.update(spec)

        return spec, delta
