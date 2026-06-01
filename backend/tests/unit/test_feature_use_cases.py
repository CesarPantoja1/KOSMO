import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.features.apply_improvement import (  # noqa: E402
    ApplyFeatureImprovementUseCase,
)
from kosmo.application.features.create_feature import (  # noqa: E402
    CreateFeatureUseCase,
)
from kosmo.application.features.generate_features import (  # noqa: E402
    GenerateFeaturesUseCase,
)
from kosmo.application.features.get_requirements import (  # noqa: E402
    GetFeatureRequirementsUseCase,
)
from kosmo.application.features.improve_feature import (  # noqa: E402
    ImproveFeatureSuggestionUseCase,
)
from kosmo.application.features.suggest_from_idea import (  # noqa: E402
    SuggestFeatureFromIdeaUseCase,
)
from kosmo.application.features.toggle_feature_status import (  # noqa: E402
    ToggleFeatureStatusUseCase,
)
from kosmo.application.features.update_requirements import (  # noqa: E402
    UpdateFeatureRequirementsUseCase,
)
from kosmo.contracts.llm.ports import LLMResponse  # noqa: E402
from kosmo.contracts.sdd.discovery import DiscoveryDocument  # noqa: E402
from kosmo.contracts.sdd.ears import (  # noqa: E402
    AcceptanceCriterion,
    EARSPattern,
    EARSRequirement,
)
from kosmo.contracts.sdd.errors import (  # noqa: E402
    FeatureNotEditableError,
    FeatureNotFoundError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature, FeatureStatus  # noqa: E402
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, RequirementId  # noqa: E402
from kosmo.contracts.sdd.project import Project, ProjectPhase  # noqa: E402
from kosmo.contracts.sdd.requirements_document import (  # noqa: E402
    RequirementsDocument,
)
from kosmo.contracts.sdd.spec import SpecDocument  # noqa: E402
from kosmo.domain.features.status_transitions import (  # noqa: E402
    validate_feature_status_transition,
)


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self._features: dict[str, Feature] = {}

    async def add(self, feature: Feature) -> None:
        self._features[feature.id] = feature

    async def get_by_project(self, project_id: ProjectId) -> list[Feature]:
        return [f for f in self._features.values() if f.project_id == project_id]

    async def get(self, feature_id: FeatureId) -> Feature | None:
        return self._features.get(feature_id)

    async def get_by_slug(self, project_id: ProjectId, slug: str) -> Feature | None:
        for f in self._features.values():
            if f.project_id == project_id and f.slug == slug:
                return f
        return None

    async def delete(self, feature_id: FeatureId) -> None:
        self._features.pop(feature_id, None)

    async def update(self, feature: Feature) -> None:
        self._features[feature.id] = feature

    async def update_requirements(
        self, feature_id: FeatureId, requirements: RequirementsDocument
    ) -> None:
        existing = self._features.get(feature_id)
        if existing is None:
            return
        self._features[feature_id] = Feature(
            id=existing.id,
            project_id=existing.project_id,
            title=existing.title,
            description=existing.description,
            status=existing.status,
            requirements=requirements,
            created_at=existing.created_at,
        )


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._documents: dict[str, dict] = {}

    async def add(self, project: Project) -> None:
        self._projects[project.id] = project

    async def get(self, project_id: ProjectId) -> Project | None:
        return self._projects.get(project_id)

    async def get_by_slug(self, slug: str) -> Project | None:
        for p in self._projects.values():
            if p.slug == slug:
                return p
        return None

    async def list_all(self) -> list[Project]:
        return list(self._projects.values())

    async def update(self, project: Project) -> None:
        self._projects[project.id] = project

    async def update_discovery_document(self, project_id: ProjectId, document: dict) -> None:
        self._documents[project_id] = document

    async def get_discovery_document(self, project_id: ProjectId) -> dict | None:
        return self._documents.get(project_id)


class InMemorySpecRepository:
    def __init__(self) -> None:
        self._specs: dict[str, SpecDocument] = {}

    async def add(self, spec: SpecDocument) -> None:
        self._specs[spec.id] = spec

    async def get(self, spec_id: Any) -> SpecDocument | None:
        return self._specs.get(str(spec_id))

    async def update(self, spec: SpecDocument) -> None:
        self._specs[spec.id] = spec

    async def list_by_project(self, project_id: ProjectId) -> list[SpecDocument]:
        return [s for s in self._specs.values() if s.project_id == project_id]


class NoopLLMClient:
    async def complete(
        self,
        _prompt: object = None,
        _temperature: float = 0,
        **_kwargs: object,
    ) -> LLMResponse:
        return LLMResponse(
            content='[{"title": "Feature from AI", "description": "AI suggested feature."}]',
            model="noop",
        )


def _make_project(project_id: str = "p-1") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        description="Test project",
        current_phase=ProjectPhase.CARACTERISTICAS,
    )


def _make_feature(
    feature_id: str = "f-1",
    project_id: str = "p-1",
    status: FeatureStatus = FeatureStatus.BORRADOR,
) -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        project_id=ProjectId(project_id),
        title="Feature de prueba",
        description="Descripcion de prueba",
        status=status,
    )


def _make_discovery() -> DiscoveryDocument:
    return DiscoveryDocument(
        vision="Ayudar a negocios a gestionar inventario",
        problem_space="Falta de visibilidad de stock",
        actors="Administradores, vendedores",
        value_proposition="Reduccion de perdidas por stock vencido",
        use_cases="Recepcion de mercaderia, venta al publico",
        core_capabilities="Control de inventario en tiempo real",
        business_rules="No se puede vender producto vencido",
        quality_attributes="Disponibilidad 99.9%",
        scope="MVP con modulo de inventario y ventas",
    )


# ── status_transitions ──────────────────────────────────────────────


class TestStatusTransitions:
    def test_borrador_to_aprobada_is_allowed(self) -> None:
        assert (
            validate_feature_status_transition(FeatureStatus.BORRADOR, FeatureStatus.APROBADA)
            is True
        )

    def test_aprobada_to_borrador_is_allowed(self) -> None:
        assert (
            validate_feature_status_transition(FeatureStatus.APROBADA, FeatureStatus.BORRADOR)
            is True
        )

    def test_borrador_to_borrador_is_rejected(self) -> None:
        assert (
            validate_feature_status_transition(FeatureStatus.BORRADOR, FeatureStatus.BORRADOR)
            is False
        )

    def test_aprobada_to_aprobada_is_rejected(self) -> None:
        assert (
            validate_feature_status_transition(FeatureStatus.APROBADA, FeatureStatus.APROBADA)
            is False
        )


# ── CreateFeatureUseCase ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_feature_is_unitario() -> None:
    feature_repo = InMemoryFeatureRepository()
    project_repo = InMemoryProjectRepository()
    await project_repo.add(_make_project())

    uc = CreateFeatureUseCase(feature_repo=feature_repo, project_repo=project_repo)
    feature = await uc.execute(
        ProjectId("p-1"),
        title="Gestion de inventario",
        description="Control de stock en tiempo real",
    )

    assert feature.title == "Gestion de inventario"
    assert feature.status == FeatureStatus.BORRADOR
    assert len(await feature_repo.get_by_project(ProjectId("p-1"))) == 1


@pytest.mark.asyncio
async def test_create_feature_rejects_missing_project() -> None:
    feature_repo = InMemoryFeatureRepository()
    project_repo = InMemoryProjectRepository()

    uc = CreateFeatureUseCase(feature_repo=feature_repo, project_repo=project_repo)
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            ProjectId("no-existe"),
            title="X",
            description="Y",
        )


# ── GenerateFeaturesUseCase ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_features_persists_5() -> None:
    feature_repo = InMemoryFeatureRepository()
    project_repo = InMemoryProjectRepository()
    await project_repo.add(_make_project())
    await project_repo.update_discovery_document(
        ProjectId("p-1"),
        {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Visión"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Gestión de inventario."}],
                },
            ],
        },
    )
    llm = NoopLLMClient()

    uc = GenerateFeaturesUseCase(
        feature_repo=feature_repo,
        project_repo=project_repo,
        llm_client=llm,
    )
    features = await uc.execute(ProjectId("p-1"))

    assert len(features) >= 1
    assert features[0].title == "Feature from AI"
    persisted = await feature_repo.get_by_project(ProjectId("p-1"))
    assert len(persisted) >= 1


@pytest.mark.asyncio
async def test_generate_features_dedups_existing() -> None:
    feature_repo = InMemoryFeatureRepository()
    project_repo = InMemoryProjectRepository()
    await project_repo.add(_make_project())
    await project_repo.update_discovery_document(
        ProjectId("p-1"),
        {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Doc"}]},
            ],
        },
    )

    class TitleMatchingLLM(NoopLLMClient):
        async def complete(
            self,
            _prompt: object = None,
            _temperature: float = 0,
            **_kwargs: object,
        ) -> LLMResponse:
            return LLMResponse(
                content='[{"title": "Feature from AI", "description": "X."}]',
                model="noop",
            )

    await feature_repo.add(
        Feature(
            id=FeatureId("f-existing"),
            project_id=ProjectId("p-1"),
            title="Feature from AI",
            description="Already exists",
            status=FeatureStatus.BORRADOR,
        )
    )

    uc = GenerateFeaturesUseCase(
        feature_repo=feature_repo,
        project_repo=project_repo,
        llm_client=TitleMatchingLLM(),
    )
    features = await uc.execute(ProjectId("p-1"))

    assert len(features) == 0


@pytest.mark.asyncio
async def test_generate_features_returns_empty_without_discovery() -> None:
    feature_repo = InMemoryFeatureRepository()
    project_repo = InMemoryProjectRepository()
    await project_repo.add(_make_project())

    uc = GenerateFeaturesUseCase(
        feature_repo=feature_repo,
        project_repo=project_repo,
        llm_client=NoopLLMClient(),
    )
    features = await uc.execute(ProjectId("p-1"))

    assert features == []


# ── ToggleFeatureStatusUseCase ───────────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_borrador_to_aprobada() -> None:
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.add(_make_feature(status=FeatureStatus.BORRADOR))

    uc = ToggleFeatureStatusUseCase(feature_repo=feature_repo)
    result = await uc.execute(FeatureId("f-1"))

    assert result.status == FeatureStatus.APROBADA


@pytest.mark.asyncio
async def test_toggle_aprobada_to_borrador() -> None:
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.add(_make_feature(status=FeatureStatus.APROBADA))

    uc = ToggleFeatureStatusUseCase(feature_repo=feature_repo)
    result = await uc.execute(FeatureId("f-1"))

    assert result.status == FeatureStatus.BORRADOR


@pytest.mark.asyncio
async def test_toggle_missing_feature_raises() -> None:
    feature_repo = InMemoryFeatureRepository()

    uc = ToggleFeatureStatusUseCase(feature_repo=feature_repo)
    with pytest.raises(FeatureNotFoundError):
        await uc.execute(FeatureId("no-existe"))


# ── ApplyFeatureImprovementUseCase ───────────────────────────────────


@pytest.mark.asyncio
async def test_apply_improvement_on_borrador_succeeds() -> None:
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.add(_make_feature(status=FeatureStatus.BORRADOR))

    uc = ApplyFeatureImprovementUseCase(feature_repo=feature_repo)
    result = await uc.execute(
        FeatureId("f-1"),
        title="Nuevo titulo mejorado",
        description="Nueva descripcion mejorada",
    )

    assert result.title == "Nuevo titulo mejorado"
    assert result.description == "Nueva descripcion mejorada"


@pytest.mark.asyncio
async def test_apply_improvement_on_aprobada_raises() -> None:
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.add(_make_feature(status=FeatureStatus.APROBADA))

    uc = ApplyFeatureImprovementUseCase(feature_repo=feature_repo)
    with pytest.raises(FeatureNotEditableError):
        await uc.execute(
            FeatureId("f-1"),
            title="Nuevo titulo",
            description="Nueva descripcion",
        )


# ── ImproveFeatureSuggestionUseCase ──────────────────────────────────


@pytest.mark.asyncio
async def test_improve_suggestion_on_borrador_succeeds() -> None:
    feature_repo = InMemoryFeatureRepository()
    project_repo = InMemoryProjectRepository()
    await project_repo.add(_make_project())
    await project_repo.update_discovery_document(
        ProjectId("p-1"),
        {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Contexto."}]}],
        },
    )
    await feature_repo.add(
        Feature(
            id=FeatureId("f-1"),
            project_id=ProjectId("p-1"),
            title="Feature de prueba",
            description="Descripcion de prueba",
            status=FeatureStatus.BORRADOR,
        )
    )

    class ImproveNoopLLM(NoopLLMClient):
        async def complete(
            self,
            _prompt: object = None,
            _temperature: float = 0,
            **_kwargs: object,
        ) -> LLMResponse:
            return LLMResponse(
                content='{"title": "Feature mejorada", "description": "Descripcion mejorada IA."}',
                model="noop",
            )

    uc = ImproveFeatureSuggestionUseCase(
        feature_repo=feature_repo,
        project_repo=project_repo,
        llm_client=ImproveNoopLLM(),
    )
    suggestion = await uc.execute(FeatureId("f-1"))

    assert suggestion.title == "Feature mejorada"
    assert suggestion.description == "Descripcion mejorada IA."


@pytest.mark.asyncio
async def test_improve_suggestion_on_aprobada_raises() -> None:
    feature_repo = InMemoryFeatureRepository()
    project_repo = InMemoryProjectRepository()
    await project_repo.add(_make_project())
    await feature_repo.add(
        Feature(
            id=FeatureId("f-1"),
            project_id=ProjectId("p-1"),
            title="Feature aprobada",
            description="Ya fue aprobada",
            status=FeatureStatus.APROBADA,
        )
    )

    uc = ImproveFeatureSuggestionUseCase(
        feature_repo=feature_repo,
        project_repo=project_repo,
        llm_client=NoopLLMClient(),
    )
    with pytest.raises(FeatureNotEditableError):
        await uc.execute(FeatureId("f-1"))


# ── UpdateFeatureRequirementsUseCase ─────────────────────────────────


@pytest.mark.asyncio
async def test_update_requirements_partial_preserves_other_categories() -> None:
    feature_repo = InMemoryFeatureRepository()
    existing_req = EARSRequirement(
        id=RequirementId("R-1"),
        pattern=EARSPattern.UBIQUITOUS,
        system="El sistema",
        response="debe validar usuarios",
        source_statement="El sistema debe validar usuarios.",
        acceptance_criteria=[AcceptanceCriterion(description="Usuarios validados")],
    )
    existing_doc = RequirementsDocument(ubiquitous=[existing_req])
    await feature_repo.add(
        Feature(
            id=FeatureId("f-1"),
            project_id=ProjectId("p-1"),
            title="Feature",
            description="Desc",
            status=FeatureStatus.APROBADA,
            requirements=existing_doc,
        )
    )

    uc = UpdateFeatureRequirementsUseCase(feature_repo=feature_repo)
    new_event = EARSRequirement(
        id=RequirementId("R-2"),
        pattern=EARSPattern.EVENT,
        trigger="WHEN usuario hace clic",
        system="El sistema",
        response="debe mostrar el panel",
        source_statement="WHEN usuario hace clic, el sistema debe mostrar el panel.",
        acceptance_criteria=[AcceptanceCriterion(description="Panel visible")],
    )
    updates = {"event": [new_event.model_dump()]}

    feature, result = await uc.execute(FeatureId("f-1"), updates)

    assert len(result.ubiquitous) == 1
    assert result.ubiquitous[0].id == "R-1"
    assert len(result.event) == 1
    assert result.event[0].system == "El sistema"
    assert len(result.state) == 0
    assert len(result.optional) == 0
    assert len(result.unwanted) == 0
    assert len(result.complex) == 0


@pytest.mark.asyncio
async def test_update_requirements_on_missing_feature_raises() -> None:
    feature_repo = InMemoryFeatureRepository()

    uc = UpdateFeatureRequirementsUseCase(feature_repo=feature_repo)
    with pytest.raises(FeatureNotFoundError):
        await uc.execute(FeatureId("no-existe"), {})


# ── GetFeatureRequirementsUseCase ──────────────────────────────────


@pytest.mark.asyncio
async def test_get_requirements_returns_empty_doc_when_none_stored() -> None:
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.add(
        Feature(
            id=FeatureId("f-1"),
            project_id=ProjectId("p-1"),
            title="Feature sin requisitos",
            description="Sin reqs",
            status=FeatureStatus.APROBADA,
        )
    )

    uc = GetFeatureRequirementsUseCase(feature_repo=feature_repo)
    feature, doc = await uc.execute(FeatureId("f-1"))

    assert doc.total == 0


# ── SuggestFeatureFromIdeaUseCase ─────────────────────────────────────


class SuggestFromIdeaNoopLLM(NoopLLMClient):
    async def complete(
        self,
        _prompt: object = None,
        _temperature: float = 0,
        **_kwargs: object,
    ) -> LLMResponse:
        return LLMResponse(
            content=(
                '{"title": "Gestion de alertas de stock", '
                '"description": "Descripcion formalizada por IA."}'
            ),
            model="noop",
        )


@pytest.mark.asyncio
async def test_suggest_from_idea_returns_single_suggestion() -> None:
    project_repo = InMemoryProjectRepository()
    await project_repo.add(_make_project())
    await project_repo.update_discovery_document(
        ProjectId("p-1"),
        {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Contexto."}]}],
        },
    )

    uc = SuggestFeatureFromIdeaUseCase(
        project_repo=project_repo,
        llm_client=SuggestFromIdeaNoopLLM(),
    )
    suggestion = await uc.execute(ProjectId("p-1"), idea="Alertas de stock bajo")

    assert suggestion.title == "Gestion de alertas de stock"
    assert suggestion.description == "Descripcion formalizada por IA."
    assert suggestion.status == FeatureStatus.BORRADOR


@pytest.mark.asyncio
async def test_suggest_from_idea_works_without_discovery() -> None:
    project_repo = InMemoryProjectRepository()
    await project_repo.add(_make_project())

    uc = SuggestFeatureFromIdeaUseCase(
        project_repo=project_repo,
        llm_client=SuggestFromIdeaNoopLLM(),
    )
    suggestion = await uc.execute(ProjectId("p-1"), idea="Alertas de stock bajo")

    assert suggestion.title == "Gestion de alertas de stock"


@pytest.mark.asyncio
async def test_suggest_from_idea_rejects_missing_project() -> None:
    project_repo = InMemoryProjectRepository()

    uc = SuggestFeatureFromIdeaUseCase(
        project_repo=project_repo,
        llm_client=SuggestFromIdeaNoopLLM(),
    )
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(ProjectId("no-existe"), idea="Cualquier idea")
