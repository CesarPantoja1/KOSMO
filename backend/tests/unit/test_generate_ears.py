import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.requirements.generate_ears import (
    GenerateEARSInput,
    GenerateEARSOutput,
    GenerateEARSUseCase,
)
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    FeatureNotFoundError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    async def by_id(self, project_id: ProjectId) -> Project | None:
        return self.projects.get(str(project_id))

    async def by_slug(self, owner_id: str, slug: str) -> Project | None:
        return next(
            (p for p in self.projects.values() if str(p.owner_id) == owner_id and p.slug == slug),
            None,
        )

    async def find_by_slug(self, slug: str) -> Project | None:
        return next((p for p in self.projects.values() if p.slug == slug), None)

    async def list_by_owner(self, owner_id: str) -> list[Project]:
        return [p for p in self.projects.values() if str(p.owner_id) == owner_id]

    async def save(self, project: Project) -> Project:  # type: ignore[override]
        self.projects[str(project.id)] = project
        return project


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}

    async def by_id(self, feature_id: FeatureId) -> Feature | None:
        return self.features.get(str(feature_id))

    async def list_by_project(self, project_id: ProjectId) -> list[Feature]:
        return [f for f in self.features.values() if str(f.project_id) == str(project_id)]

    async def save(self, feature: Feature) -> Feature:  # type: ignore[override]
        self.features[str(feature.id)] = feature
        return feature

    async def save_many(self, features: list[Feature]) -> list[Feature]:
        for f in features:
            self.features[str(f.id)] = f
        return features

    async def next_number(self, project_id: ProjectId) -> int:
        project_features = await self.list_by_project(project_id)
        return max((f.number for f in project_features), default=0) + 1


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self._discovery: dict[str, RichTextDocument] = {}

    async def get_discovery(self, project_id: ProjectId) -> RichTextDocument | None:
        return self._discovery.get(str(project_id))

    async def save_discovery(
        self, project_id: ProjectId, document: RichTextDocument
    ) -> RichTextDocument:
        self._discovery[str(project_id)] = document
        return document

    async def get_requirements(
        self,
        feature_id: FeatureId,  # noqa: ARG002
    ) -> RichTextDocument | None:  # type: ignore[override]
        return None

    async def save_requirements(
        self,
        feature_id: FeatureId,  # noqa: ARG002
        document: RichTextDocument,  # noqa: ARG002
    ) -> RichTextDocument:  # type: ignore[override]
        return document


class InMemoryRequirementRepository:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def by_feature_id(self, feature_id: FeatureId) -> str | None:
        return self._data.get(str(feature_id))

    async def save(self, feature_id: FeatureId, markdown: str) -> None:
        self._data[str(feature_id)] = markdown


class MockLLMClient:
    def __init__(self, response_text: str = "") -> None:
        self.last_prompt: Any = None
        self.response_text = response_text

    async def complete(
        self,
        prompt: Any,
        temperature: float = 0.3,  # noqa: ARG002
        max_tokens: int = 4096,  # noqa: ARG002
    ) -> Any:
        from kosmo.contracts.llm.ports import LLMResponse, LLMUsage

        self.last_prompt = prompt
        return LLMResponse(
            text=self.response_text,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300),
            model="mock-model",
            finish_reason="stop",
        )

    async def complete_json(
        self,
        prompt: Any,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Any:
        return await self.complete(prompt, temperature, max_tokens)


VALID_EARS_JSON = """```json
{
  "requirements": [
    {
      "pattern": "ubiquitous",
      "source_statement": "El sistema shall registrar la operación del usuario",
      "trigger": "",
      "system": "el sistema",
      "response": "registrar la operación del usuario",
      "rationale": "Auditoría de operaciones",
      "acceptance_criteria": [
        {
          "given": "Una operación del usuario",
          "when": "El usuario realiza la operación",
          "then": "El sistema registra la operación"
        }
      ],
      "traceability": ["C01"],
      "feature_number": 1,
      "requirement_number": 1
    },
    {
      "pattern": "event_driven",
      "source_statement": "Cuando el usuario inicia sesión, el sistema shall mostrar el dashboard",
      "trigger": "el usuario inicia sesión",
      "system": "el sistema",
      "response": "mostrar el dashboard",
      "rationale": "Navegación post-autenticación",
      "acceptance_criteria": [
        {
          "given": "Un usuario autenticado",
          "when": "El usuario inicia sesión",
          "then": "El sistema muestra el dashboard"
        }
      ],
      "traceability": ["C01"],
      "feature_number": 1,
      "requirement_number": 2
    },
    {
      "pattern": "state_driven",
      "source_statement": "Mientras la sesión está activa, el sistema shall mantener los datos",
      "trigger": "la sesión está activa",
      "system": "el sistema",
      "response": "mantener los datos de contexto",
      "rationale": "Persistencia de contexto",
      "acceptance_criteria": [
        {
          "given": "Una sesión activa",
          "when": "El usuario navega",
          "then": "El sistema mantiene los datos de contexto"
        }
      ],
      "traceability": ["C02"],
      "feature_number": 1,
      "requirement_number": 3
    },
    {
      "pattern": "optional",
      "source_statement": "Donde se selecciona modo oscuro, el sistema shall aplicar tema oscuro",
      "trigger": "el usuario selecciona modo oscuro",
      "system": "el sistema",
      "response": "aplicar el tema oscuro",
      "rationale": "Personalización de interfaz",
      "acceptance_criteria": [
        {
          "given": "El usuario selecciona modo oscuro",
          "when": "El usuario cambia la preferencia",
          "then": "El sistema aplica el tema oscuro"
        }
      ],
      "traceability": ["C03"],
      "feature_number": 1,
      "requirement_number": 4
    }
  ]
}
```"""


@pytest.mark.asyncio
async def test_generate_ears_success() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    document_repo: Any = InMemoryDocumentRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    llm_client = MockLLMClient(response_text=VALID_EARS_JSON)

    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        llm_client=llm_client,
    )

    project = Project(
        id=ProjectId("prj_ears01"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_ears01"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_ears01"),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature for EARS",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    await document_repo.save_discovery(project.id, RichTextDocument(nodes=[]))

    input_data = GenerateEARSInput(
        project_id=ProjectId("prj_ears01"),
        feature_id=FeatureId("feat_ears01"),
    )

    # Act
    with patch("kosmo.application.requirements.generate_ears.IdGenerator") as mock_id_generator:
        mock_id_generator.generate.return_value = "req_01HT1234567890"
        result = await use_case.execute(input_data)

    # Assert
    assert isinstance(result, GenerateEARSOutput)
    assert result.project_id == ProjectId("prj_ears01")
    assert result.feature_id == FeatureId("feat_ears01")
    assert len(result.requirements) == 4
    assert result.phase_output is not None
    assert result.phase_output.generation_metadata.llm_calls == 1


@pytest.mark.asyncio
async def test_generate_ears_raises_project_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    document_repo: Any = InMemoryDocumentRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    llm_client = MockLLMClient()

    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        llm_client=llm_client,
    )

    input_data = GenerateEARSInput(
        project_id=ProjectId("prj_nonexistent"),
        feature_id=FeatureId("feat_ears02"),
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await use_case.execute(input_data)


@pytest.mark.asyncio
async def test_generate_ears_raises_feature_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    document_repo: Any = InMemoryDocumentRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    llm_client = MockLLMClient()

    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        llm_client=llm_client,
    )

    project = Project(
        id=ProjectId("prj_ears03"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_ears03"),
    )
    await project_repo.save(project)

    input_data = GenerateEARSInput(
        project_id=ProjectId("prj_ears03"),
        feature_id=FeatureId("feat_nonexistent"),
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await use_case.execute(input_data)


@pytest.mark.asyncio
async def test_generate_ears_raises_document_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    document_repo: Any = InMemoryDocumentRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    llm_client = MockLLMClient()

    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        llm_client=llm_client,
    )

    project = Project(
        id=ProjectId("prj_ears04"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_ears04"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_ears04"),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    input_data = GenerateEARSInput(
        project_id=ProjectId("prj_ears04"),
        feature_id=FeatureId("feat_ears04"),
    )

    # Act & Assert
    with pytest.raises(DocumentNotFoundError):
        await use_case.execute(input_data)


@pytest.mark.asyncio
async def test_generate_ears_persists_requirements_markdown() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    document_repo: Any = InMemoryDocumentRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    llm_client = MockLLMClient(response_text=VALID_EARS_JSON)

    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        llm_client=llm_client,
    )

    project = Project(
        id=ProjectId("prj_ears05"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_ears05"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_ears05"),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    await document_repo.save_discovery(project.id, RichTextDocument(nodes=[]))

    input_data = GenerateEARSInput(
        project_id=ProjectId("prj_ears05"),
        feature_id=FeatureId("feat_ears05"),
    )

    # Act
    with patch("kosmo.application.requirements.generate_ears.IdGenerator") as mock_id_generator:
        mock_id_generator.generate.return_value = "req_01HT1234567890"
        await use_case.execute(input_data)

    # Assert
    saved = await requirement_repo.by_feature_id(FeatureId("feat_ears05"))
    assert saved is not None
    assert "### REQ-1.1  Ubiquitous" in saved
    assert "### REQ-1.2  Event-Driven" in saved
    assert "El sistema shall registrar la operación del usuario" in saved
    assert "Criterios de Aceptación" not in saved


STRICT_FAILING_EARS_JSON = """```json
{
  "requirements": [
    {
      "pattern": "ubiquitous",
      "source_statement": "El inventario siempre será auditado por la plataforma",
      "rationale": "Trazabilidad",
      "feature_number": 6,
      "requirement_number": 1
    },
    {
      "pattern": "event_driven",
      "source_statement": "Cuando se confirme una venta, el sistema debe seguir el protocolo",
      "rationale": "Registro",
      "feature_number": 6,
      "requirement_number": 2
    },
    {
      "pattern": "state_driven",
      "source_statement": "Mientras la sesión esté activa, el sistema debe mantener el contexto",
      "rationale": "Contexto",
      "feature_number": 6,
      "requirement_number": 3
    }
  ]
}
```"""


@pytest.mark.asyncio
async def test_generate_ears_succeeds_despite_syntax_and_leak_warnings() -> None:
    # El output tiene un ubiquitous que no matchea la regex estricta y el término
    # "protocolo": antes eran errores duros (502). Ahora son warnings y debe persistir.
    project_repo: Any = InMemoryProjectRepository()
    feature_repo: Any = InMemoryFeatureRepository()
    document_repo: Any = InMemoryDocumentRepository()
    requirement_repo: Any = InMemoryRequirementRepository()
    llm_client = MockLLMClient(response_text=STRICT_FAILING_EARS_JSON)

    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=document_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        llm_client=llm_client,
    )

    project = Project(
        id=ProjectId("prj_ears06"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_ears06"),
    )
    await project_repo.save(project)

    feature = Feature(
        id=FeatureId("feat_ears06"),
        number=6,
        title="Kardex",
        slug="kardex",
        description="Movimientos de inventario",
        project_id=project.id,
    )
    await feature_repo.save(feature)

    await document_repo.save_discovery(project.id, RichTextDocument(nodes=[]))

    input_data = GenerateEARSInput(
        project_id=ProjectId("prj_ears06"),
        feature_id=FeatureId("feat_ears06"),
    )

    # Act
    with patch("kosmo.application.requirements.generate_ears.IdGenerator") as mock_id_generator:
        mock_id_generator.generate.return_value = "req_01HT1234567890"
        result = await use_case.execute(input_data)

    # Assert
    assert isinstance(result, GenerateEARSOutput)
    assert result.phase_output.validation_result.is_valid is True
    assert result.phase_output.generation_metadata.llm_calls == 1
    assert len(result.requirements) == 3
    saved = await requirement_repo.by_feature_id(FeatureId("feat_ears06"))
    assert saved is not None
    assert "REQ-6.1" in saved
