from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.ids import SpecId
from kosmo.contracts.sdd.repositories import SpecRepository
from kosmo.contracts.sdd.spec import SpecDocument, SpecPhase
from kosmo.contracts.sdd.tasks import Task
from kosmo.domain.agents.planner.service import decompose_tasks


class DecomposeTasksUseCase:
    def __init__(
        self,
        spec_repo: SpecRepository,
        llm_client: LLMClient,
    ) -> None:
        self._spec_repo = spec_repo
        self._llm_client = llm_client

    async def execute(self, spec_id: SpecId) -> SpecDocument:
        spec = await self._spec_repo.get(spec_id)
        if spec is None:
            raise Exception(f"Especificacion no encontrada: {spec_id}")

        if spec.design is None:
            raise Exception("La especificacion no tiene diseno generado")

        tasks: list[Task] = await decompose_tasks(
            domain_model=spec.design,
            constitution=spec.constitution,
            llm_client=self._llm_client,
        )

        spec.tasks = tasks
        spec.phase = SpecPhase.PROTOTIPO
        await self._spec_repo.update(spec)

        return spec
