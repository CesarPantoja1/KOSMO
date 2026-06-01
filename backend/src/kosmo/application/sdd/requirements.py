from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.ids import SpecId
from kosmo.contracts.sdd.repositories import SpecRepository
from kosmo.contracts.sdd.spec import SpecDocument, SpecPhase
from kosmo.domain.agents.analyzer.service import generate_requirements


class GenerateRequirementsUseCase:
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

        if spec.discovery is None:
            raise Exception("La especificacion no tiene un Descubrimiento generado")

        constitution = spec.constitution

        requirements: list[EARSRequirement] = await generate_requirements(
            discovery=spec.discovery,
            constitution=constitution,
            llm_client=self._llm_client,
        )

        spec.requirements = requirements
        spec.phase = SpecPhase.REQUISITOS
        await self._spec_repo.update(spec)

        return spec
