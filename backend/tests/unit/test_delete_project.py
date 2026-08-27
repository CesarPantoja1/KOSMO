from __future__ import annotations

import pytest

from kosmo.application.projects.delete_project import (
    DeleteProjectInput,
    DeleteProjectUseCase,
)
from kosmo.contracts.ai.chat import ChatRole, ChatSession, MensajeChat
from kosmo.contracts.ai.consistency import ConsistencyEvaluation, ConsistencyEvaluationStatus
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import (
    ActivityDiagramId,
    ChatMessageId,
    ChatSessionId,
    ConsistencyEvaluationId,
    FeatureId,
    ProjectId,
    UserId,
)
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    InMemoryActivityDiagramRepository,
    InMemoryChatRepository,
    InMemoryConsistencyEvaluationRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
    InMemoryTraceabilityRepository,
)

_OWNER = UserId("usr_owner")


class _AgentMemorySpy:
    def __init__(self) -> None:
        self.deleted_projects: list[str] = []

    async def delete_by_project(self, project_id: ProjectId) -> None:
        self.deleted_projects.append(str(project_id))


class _WorkspaceManagerSpy:
    def __init__(self) -> None:
        self.deleted_projects: list[str] = []

    async def delete_workspace(self, project_id: ProjectId) -> None:
        self.deleted_projects.append(str(project_id))


def _a_project(project_id: str = "prj_cascade") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=_OWNER,
    )


def _a_feature(project: Project, feature_id: str, number: int = 1) -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        project_id=project.id,
        number=number,
        title="Test Feature",
        slug="test-feature",
        description="Descripción",
    )


def _a_diagram(feature: Feature) -> DiagramaActividad:
    return DiagramaActividad(
        id=ActivityDiagramId(f"adg_{str(feature.id)[-4:]}"),
        feature_id=feature.id,
        diagram_syntax="@startuml\nstart\n:accion;\nstop\n@enduml",
    )


def _make_uc(
    project_repo: InMemoryProjectRepository,
    feature_repo: InMemoryFeatureRepository,
    requirement_repo: InMemoryRequirementRepository,
    diagram_repo: InMemoryActivityDiagramRepository,
    document_repo: InMemoryDocumentRepository,
    chat_repo: InMemoryChatRepository,
    evaluation_repo: InMemoryConsistencyEvaluationRepository,
    traceability_repo: InMemoryTraceabilityRepository,
    agent_memory: _AgentMemorySpy | None = None,
    workspace_manager: _WorkspaceManagerSpy | None = None,
) -> DeleteProjectUseCase:
    return DeleteProjectUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        document_repo=document_repo,
        chat_repo=chat_repo,
        consistency_evaluation_repo=evaluation_repo,
        traceability_repo=traceability_repo,
        agent_memory=agent_memory,
        workspace_manager=workspace_manager,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_project_removes_all_artifacts_in_cascade() -> None:
    # Arrange — sembrar todos los artefactos del proyecto
    project = _a_project()
    feature_1 = _a_feature(project, "feat_cascade1", number=1)
    feature_2 = _a_feature(project, "feat_cascade2", number=2)

    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    await feature_repo.save(feature_1)
    await feature_repo.save(feature_2)

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature_1.id, "### REQ-1.1\n\nRequisito uno.")
    await requirement_repo.save(feature_2.id, "### REQ-2.1\n\nRequisito dos.")

    diagram_repo = InMemoryActivityDiagramRepository()
    await diagram_repo.save(_a_diagram(feature_1))

    document_repo = InMemoryDocumentRepository()
    await document_repo.save_discovery(project.id, RichTextDocument(nodes=[]))
    await document_repo.save_version(project.id, SpecPhase.DESCUBRIMIENTO, "v1", [])

    chat_repo = InMemoryChatRepository()
    session = ChatSession(id=ChatSessionId("chs_cascade"), project_id=project.id, phase=SpecPhase.DESCUBRIMIENTO)
    await chat_repo.create_session(session)
    await chat_repo.save_message(
        project.id,
        SpecPhase.DESCUBRIMIENTO,
        MensajeChat(id=ChatMessageId("chm_cascade"), role=ChatRole.USER, content="hola"),
        session_id=session.id,
    )

    evaluation_repo = InMemoryConsistencyEvaluationRepository()
    await evaluation_repo.save(
        ConsistencyEvaluation(
            id=ConsistencyEvaluationId("cev_cascade"),
            project_id=project.id,
            source_phase=SpecPhase.DESCUBRIMIENTO,
            target_phase=SpecPhase.CARACTERISTICAS,
            target_artifact_id=str(feature_1.id),
            artifact_type="Feature",
            snapshot_hash="h",
            status=ConsistencyEvaluationStatus.COMPLETED,
        )
    )

    traceability_repo = InMemoryTraceabilityRepository()
    await traceability_repo.add_edge("discovery", str(project.id), "feature", str(feature_1.id))
    await traceability_repo.add_edge("feature", str(feature_1.id), "requirement", "req_1")

    agent_memory = _AgentMemorySpy()
    use_case = _make_uc(
        project_repo,
        feature_repo,
        requirement_repo,
        diagram_repo,
        document_repo,
        chat_repo,
        evaluation_repo,
        traceability_repo,
        agent_memory,
    )

    # Act
    await use_case.execute(DeleteProjectInput(project_id=project.id, owner_id=_OWNER))

    # Assert — nada queda
    assert await project_repo.by_id(project.id) is None
    assert await feature_repo.by_id(feature_1.id) is None
    assert await feature_repo.by_id(feature_2.id) is None
    assert await requirement_repo.by_feature_id(feature_1.id) is None
    assert await requirement_repo.by_feature_id(feature_2.id) is None
    assert await diagram_repo.by_feature_id(feature_1.id) is None
    assert await document_repo.get_discovery(project.id) is None
    assert document_repo.versions == {}
    assert chat_repo.sessions == []
    assert chat_repo.messages == []
    assert await evaluation_repo.list_unresolved(project.id, SpecPhase.CARACTERISTICAS) == []
    assert traceability_repo.edges == []
    assert agent_memory.deleted_projects == [str(project.id)]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_project_raises_when_project_not_found() -> None:
    # Arrange
    use_case = _make_uc(
        InMemoryProjectRepository(),
        InMemoryFeatureRepository(),
        InMemoryRequirementRepository(),
        InMemoryActivityDiagramRepository(),
        InMemoryDocumentRepository(),
        InMemoryChatRepository(),
        InMemoryConsistencyEvaluationRepository(),
        InMemoryTraceabilityRepository(),
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(DeleteProjectInput(project_id=ProjectId("prj_missing"), owner_id=_OWNER))

    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_project_raises_when_owner_does_not_match() -> None:
    # Arrange
    project = _a_project()
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    use_case = _make_uc(
        project_repo,
        InMemoryFeatureRepository(),
        InMemoryRequirementRepository(),
        InMemoryActivityDiagramRepository(),
        InMemoryDocumentRepository(),
        InMemoryChatRepository(),
        InMemoryConsistencyEvaluationRepository(),
        InMemoryTraceabilityRepository(),
    )

    # Act & Assert — un owner ajeno no puede borrar ni conoce la existencia del proyecto
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(DeleteProjectInput(project_id=project.id, owner_id=UserId("usr_intruso")))

    assert exc_info.value.problem.status == 404
    assert await project_repo.by_id(project.id) is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_project_without_artifacts_keeps_working() -> None:
    # Arrange — proyecto sin descubrimiento, features ni artefactos secundarios
    project = _a_project("prj_empty")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    use_case = _make_uc(
        project_repo,
        InMemoryFeatureRepository(),
        InMemoryRequirementRepository(),
        InMemoryActivityDiagramRepository(),
        InMemoryDocumentRepository(),
        InMemoryChatRepository(),
        InMemoryConsistencyEvaluationRepository(),
        InMemoryTraceabilityRepository(),
    )

    # Act & Assert — el borrado solo elimina lo que exista
    await use_case.execute(DeleteProjectInput(project_id=project.id, owner_id=_OWNER))
    assert await project_repo.by_id(project.id) is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_delete_project_removes_persisted_workspace() -> None:
    project = _a_project("prj_workspace")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)
    workspace_manager = _WorkspaceManagerSpy()

    use_case = _make_uc(
        project_repo,
        InMemoryFeatureRepository(),
        InMemoryRequirementRepository(),
        InMemoryActivityDiagramRepository(),
        InMemoryDocumentRepository(),
        InMemoryChatRepository(),
        InMemoryConsistencyEvaluationRepository(),
        InMemoryTraceabilityRepository(),
        workspace_manager=workspace_manager,
    )

    await use_case.execute(DeleteProjectInput(project_id=project.id, owner_id=_OWNER))

    assert workspace_manager.deleted_projects == [str(project.id)]
