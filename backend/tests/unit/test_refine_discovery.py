from __future__ import annotations

import pytest

from kosmo.application.discovery.refine_discovery import (
    RefineDiscoveryInput,
    RefineDiscoveryUseCase,
)
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    InMemoryDocumentRepository,
    InMemoryOutbox,
    InMemoryProjectRepository,
)


class _StubRefineAgent:
    async def execute_with_skill(
        self,
        skill_name: str,  # noqa: ARG002
        context: object,  # noqa: ARG002
        *,
        project_id: object | None = None,  # noqa: ARG002
        user_instructions: str | None = None,  # noqa: ARG002
    ) -> object:
        from kosmo.domain.sdd.document_converters import markdown_to_document

        refined = "## Visión\n\nVisión refinada.\n\n## Alcance\n\nAlcance refinado."
        return DiscoveryPhaseOutput(
            discovery_document=markdown_to_document(refined),
            validation_result=ValidationResult(is_valid=True, errors=[]),
            generation_metadata=GenerationMetadata(),
        )


class _StubContextBuilder:
    async def build_discovery_refine_context(
        self,
        *,
        project_id: ProjectId,  # noqa: ARG002
        user_instructions: str,  # noqa: ARG002
    ) -> object:
        return object()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_refine_discovery_enqueues_downstream_evaluation() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project = Project(
        id=ProjectId("prj_refine"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)

    document_repo = InMemoryDocumentRepository()
    from kosmo.domain.sdd.document_converters import markdown_to_document

    await document_repo.save_discovery(
        project.id,
        markdown_to_document("## Visión\n\nVisión original.\n\n## Alcance\n\nAlcance original."),
    )

    outbox = InMemoryOutbox()
    use_case = RefineDiscoveryUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        context_builder=_StubContextBuilder(),  # type: ignore[reportArgumentType]
        agent=_StubRefineAgent(),  # type: ignore[reportArgumentType]
        outbox=outbox,
    )

    # Act
    result = await use_case.execute(RefineDiscoveryInput(project_id=project.id, instructions="Refina la visión"))

    # Assert — refinar Descubrimiento dispara la verificación de las fases a la derecha
    assert result.project_id == project.id
    assert len(outbox.jobs) == 1
    job_type, payload = outbox.jobs[0]
    assert job_type == "consistency_evaluate"
    assert payload["project_id"] == "prj_refine"
    assert payload["source_phase"] == "descubrimiento"
    assert "Visión refinada" in payload["changes"][0]["after"]
