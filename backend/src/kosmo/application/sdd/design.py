from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.domain_model import DomainModel
from kosmo.contracts.sdd.ids import SpecId
from kosmo.contracts.sdd.repositories import SpecRepository
from kosmo.contracts.sdd.spec import SpecDocument, SpecPhase
from kosmo.domain.agents.architect.service import generate_design


class GenerateDesignUseCase:
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

        if not spec.requirements:
            raise Exception("La especificacion no tiene requisitos generados")

        design: DomainModel = await generate_design(
            requirements=spec.requirements,
            constitution=spec.constitution,
            llm_client=self._llm_client,
        )

        spec.design = design
        spec.phase = SpecPhase.MODELO
        await self._spec_repo.update(spec)

        return spec
