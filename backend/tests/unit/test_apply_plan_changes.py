import pytest

from kosmo.application.chat.apply_plan_changes import (
    ApplyPlanChangesInput,
    ApplyPlanChangesUseCase,
)
from kosmo.contracts import ChatRepository, DiffCambio, EstadoPlanCambio, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import DocumentNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import DocumentRepository, FeatureRepository, ProjectRepository
from tests.unit.fakes import (
    InMemoryChatRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
)

_DEFAULT_MARKDOWN = "## Visión\n\nContenido de visión.\n\n## Alcance\n\nContenido de alcance original."


def _make_project(project_id: str = "prj_test") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_test"),
    )


def _make_uc(
    project_repo: ProjectRepository,
    chat_repo: ChatRepository,
    document_repo: DocumentRepository,
    feature_repo: FeatureRepository | None = None,
) -> ApplyPlanChangesUseCase:
    return ApplyPlanChangesUseCase(
        project_repo=project_repo,
        chat_repo=chat_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
    )


async def _seed_document(document_repo: InMemoryDocumentRepository, project_id: ProjectId) -> None:
    from kosmo.domain.sdd.document_converters import markdown_to_document

    document_repo.discovery_docs[str(project_id)] = markdown_to_document(_DEFAULT_MARKDOWN)


def _plan_change(
    cid: str,
    before: str,
    after: str,
    status: EstadoPlanCambio = EstadoPlanCambio.ADDED,
    *,
    section: str = "Test",
    context_id: str | None = None,
) -> PlanCambio:
    return PlanCambio(
        id=PlanChangeId(cid),
        section=section,
        description="test",
        diff=DiffCambio(before=before, after=after),
        status=status,
        context_id=context_id,
    )


# ── happy path ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_replaces_and_saves() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    await _seed_document(document_repo, project.id)

    change = _plan_change("chg_01", before="Contenido de alcance original.", after="Contenido de alcance modificado.")
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, change)

    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act
    result = await uc.execute(
        ApplyPlanChangesInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            change_ids=[PlanChangeId("chg_01")],
        )
    )

    # Assert
    assert result.applied_count == 1
    assert result.failed_count == 0
    assert len(result.failed_changes) == 0

    doc = await document_repo.get_discovery(project.id)
    assert doc is not None
    from kosmo.domain.sdd.document_converters import document_to_markdown

    markdown = document_to_markdown(doc)
    assert "Contenido de alcance modificado." in markdown
    assert "Contenido de alcance original." not in markdown

    updated = chat_repo.plans[0]
    assert updated.status == EstadoPlanCambio.APPLIED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_appends_when_before_empty() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    await _seed_document(document_repo, project.id)

    change = _plan_change("chg_01", before="", after="Sección nueva")
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, change)

    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act
    result = await uc.execute(
        ApplyPlanChangesInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            change_ids=[PlanChangeId("chg_01")],
        )
    )

    # Assert
    assert result.applied_count == 1
    assert result.failed_count == 0

    from kosmo.domain.sdd.document_converters import document_to_markdown

    doc = await document_repo.get_discovery(project.id)
    assert doc is not None
    assert "Sección nueva" in document_to_markdown(doc)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_multiple_in_order() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    await _seed_document(document_repo, project.id)

    c1 = _plan_change("chg_01", before="Contenido de visión.", after="Visión actualizada.")
    c2 = _plan_change("chg_02", before="", after="Nueva sección al final")
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, c1)
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, c2)

    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act
    result = await uc.execute(
        ApplyPlanChangesInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            change_ids=[PlanChangeId("chg_01"), PlanChangeId("chg_02")],
        )
    )

    # Assert
    assert result.applied_count == 2
    assert result.failed_count == 0

    from kosmo.domain.sdd.document_converters import document_to_markdown

    doc = await document_repo.get_discovery(project.id)
    assert doc is not None
    markdown = document_to_markdown(doc)
    assert "Visión actualizada." in markdown
    assert "Nueva sección al final" in markdown


# ── partial failure ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_reports_failed_when_before_not_found() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    await _seed_document(document_repo, project.id)

    good = _plan_change("chg_01", before="Contenido de visión.", after="Visión actualizada.")
    bad = _plan_change("chg_02", before="Texto que no existe", after="Algo")
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, good)
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, bad)

    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act
    result = await uc.execute(
        ApplyPlanChangesInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            change_ids=[PlanChangeId("chg_01"), PlanChangeId("chg_02")],
        )
    )

    # Assert
    assert result.applied_count == 1
    assert result.failed_count == 1
    assert len(result.failed_changes) == 1
    assert str(result.failed_changes[0].id) == "chg_02"
    assert "fragmento original" in result.failed_changes[0].reason.lower()

    from kosmo.domain.sdd.document_converters import document_to_markdown

    doc = await document_repo.get_discovery(project.id)
    assert doc is not None
    assert "Visión actualizada." in document_to_markdown(doc)

    # chg_01 marked applied, chg_02 stays unchanged
    statuses = {str(c.id): c.status for c in chat_repo.plans}
    assert statuses["chg_01"] == EstadoPlanCambio.APPLIED
    assert statuses["chg_02"] == EstadoPlanCambio.ADDED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_reports_failed_when_change_not_in_plan() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    await _seed_document(document_repo, project.id)

    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act
    result = await uc.execute(
        ApplyPlanChangesInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            change_ids=[PlanChangeId("chg_missing")],
        )
    )

    # Assert
    assert result.applied_count == 0
    assert result.failed_count == 1
    assert str(result.failed_changes[0].id) == "chg_missing"


# ── error paths ──


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_raises_when_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            ApplyPlanChangesInput(
                project_id=ProjectId("prj_missing"),
                phase=SpecPhase.DESCUBRIMIENTO,
                change_ids=[PlanChangeId("chg_01")],
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_raises_when_document_not_found() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()

    change = _plan_change("chg_01", before="x", after="y")
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, change)

    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act & Assert
    with pytest.raises(DocumentNotFoundError):
        await uc.execute(
            ApplyPlanChangesInput(
                project_id=project.id,
                phase=SpecPhase.DESCUBRIMIENTO,
                change_ids=[PlanChangeId("chg_01")],
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_raises_value_error_for_unsupported_phase() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act & Assert
    with pytest.raises(ValueError, match="modelo"):
        await uc.execute(
            ApplyPlanChangesInput(
                project_id=project.id,
                phase=SpecPhase.MODELO,
                change_ids=[PlanChangeId("chg_01")],
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_noops_when_no_requested_changes_are_applicable() -> None:
    # Arrange
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    await _seed_document(document_repo, project.id)

    bad = _plan_change("chg_01", before="No existe en el documento", after="Algo")
    await chat_repo.add_plan_change(project.id, SpecPhase.DESCUBRIMIENTO, bad)

    uc = _make_uc(project_repo, chat_repo, document_repo)

    # Act
    result = await uc.execute(
        ApplyPlanChangesInput(
            project_id=project.id,
            phase=SpecPhase.DESCUBRIMIENTO,
            change_ids=[PlanChangeId("chg_01")],
        )
    )

    # Assert
    assert result.applied_count == 0
    assert result.failed_count == 1

    doc = await document_repo.get_discovery(project.id)
    from kosmo.domain.sdd.document_converters import document_to_markdown

    assert doc is not None
    assert document_to_markdown(doc) == _DEFAULT_MARKDOWN


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_feature_change_updates_its_target_attribute() -> None:
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    feature_repo = InMemoryFeatureRepository()
    feature = Feature(
        id=FeatureId("feat_01"), project_id=project.id, number=1,
        title="Obtener turno", slug="obtener-turno", description="El usuario toma un turno.",
    )
    await feature_repo.save(feature)
    change = _plan_change(
        "chg_feature_01", "El usuario toma un turno.", "El usuario registra su identificación y toma un turno.",
        section="Descripción", context_id="feat_01",
    )
    await chat_repo.add_plan_change(project.id, SpecPhase.CARACTERISTICAS, change)

    result = await _make_uc(project_repo, chat_repo, document_repo, feature_repo).execute(
        ApplyPlanChangesInput(project.id, SpecPhase.CARACTERISTICAS, [PlanChangeId("chg_feature_01")])
    )

    assert result.applied_count == 1
    assert result.failed_count == 0
    saved = await feature_repo.by_id(FeatureId("feat_01"))
    assert saved is not None
    assert saved.description == "El usuario registra su identificación y toma un turno."
    assert chat_repo.plans[0].status == EstadoPlanCambio.APPLIED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_feature_change_rejects_stale_text_without_modifying_feature() -> None:
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    feature_repo = InMemoryFeatureRepository()
    feature = Feature(
        id=FeatureId("feat_01"), project_id=project.id, number=1,
        title="Obtener turno", slug="obtener-turno", description="Texto editado manualmente.",
    )
    await feature_repo.save(feature)
    change = _plan_change(
        "chg_feature_01", "Texto anterior.", "Texto propuesto.", section="Descripción", context_id="feat_01",
    )
    await chat_repo.add_plan_change(project.id, SpecPhase.CARACTERISTICAS, change)

    result = await _make_uc(project_repo, chat_repo, document_repo, feature_repo).execute(
        ApplyPlanChangesInput(project.id, SpecPhase.CARACTERISTICAS, [PlanChangeId("chg_feature_01")])
    )

    assert result.applied_count == 0
    assert result.failed_count == 1
    assert "ya no se encuentra" in result.failed_changes[0].reason
    assert (await feature_repo.by_id(FeatureId("feat_01"))).description == "Texto editado manualmente."  # type: ignore[union-attr]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_apply_feature_change_without_context_resolves_a_unique_legacy_change() -> None:
    project = _make_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    chat_repo = InMemoryChatRepository()
    document_repo = InMemoryDocumentRepository()
    feature_repo = InMemoryFeatureRepository()
    feature = Feature(
        id=FeatureId("feat_01"), project_id=project.id, number=1,
        title="Obtener turno", slug="obtener-turno", description="Texto original único.",
    )
    await feature_repo.save(feature)
    change = _plan_change("chg_feature_legacy", "Texto original único.", "Texto actualizado.", section="Descripción")
    await chat_repo.add_plan_change(project.id, SpecPhase.CARACTERISTICAS, change)

    result = await _make_uc(project_repo, chat_repo, document_repo, feature_repo).execute(
        ApplyPlanChangesInput(project.id, SpecPhase.CARACTERISTICAS, [PlanChangeId("chg_feature_legacy")])
    )

    assert result.applied_count == 1
    assert (await feature_repo.by_id(FeatureId("feat_01"))).description == "Texto actualizado."  # type: ignore[union-attr]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_feature_listing_is_ordered_by_feature_number() -> None:
    project = _make_project()
    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(
        Feature(
            id=FeatureId("feat_03"), project_id=project.id, number=3,
            title="Tercera", slug="tercera", description="",
        )
    )
    await feature_repo.save(
        Feature(
            id=FeatureId("feat_01"), project_id=project.id, number=1,
            title="Primera", slug="primera", description="",
        )
    )

    listed = await feature_repo.list_by_project(project.id)

    assert [feature.number for feature in listed] == [1, 3]
