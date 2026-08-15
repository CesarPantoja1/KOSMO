from __future__ import annotations

from typing import Any

import pytest

from kosmo.application.pipeline.generation_loop import GenerationLoop
from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_modes.discovery_mode import DiscoveryMode
from tests.unit.conftest import make_discovery_document


class _StubLLM:
    async def complete_typed(
        self,
        prompt: Any,
        output_type: type[Any],
        temperature: float = 0.1,  # noqa: ARG002
        max_tokens: int = 4096,  # noqa: ARG002
    ) -> Any:
        return make_discovery_document("contenido")

    async def complete(self, prompt: Any, temperature: float = 0.3, max_tokens: int = 4096) -> Any:  # noqa: ARG002
        from kosmo.contracts.llm.ports import LLMResponse

        return LLMResponse(text="ok")


class _StubEnricher:
    async def enrich(self, system_prompt: str, base: str, project_id: Any, *, phase: Any = None) -> str:  # noqa: ARG002
        return system_prompt


class _CountingToolResolver:
    def __init__(self) -> None:
        self.calls = 0

    async def resolve(self, system_prompt: str, user_prompt: str, project_id: Any) -> tuple[str, list, list]:  # noqa: ARG002
        self.calls += 1
        return ("", [], [])

    async def resolve_knowledge_tools(self, system_prompt: str, user_prompt: str, project_id: Any) -> tuple[str, list]:  # noqa: ARG002
        return ("", [])


class _StubRecorder:
    async def record(self, **kwargs: Any) -> None:  # noqa: ARG002
        return None


class _ModeNoTools:
    """Modo de generacion desde cero: no consulta tools de conocimiento."""

    requires_enrichment = True
    requires_tool_consultation = False
    phase_name = SpecPhase.DESCUBRIMIENTO
    system_prompt = "sys"
    temperature = 0.1
    max_tokens = 100
    output_type = type(make_discovery_document(""))

    def build_user_prompt(self, context: Any) -> str:  # noqa: ARG002
        return "user"

    def validate_output(self, output: Any, *, context: Any = None) -> ValidationResult:  # noqa: ARG002
        return ValidationResult(is_valid=True, errors=[])

    def build_validation_feedback(self, errors: list[str]) -> str:  # noqa: ARG002
        return "feedback"

    def build_retry_prompt(self, original_prompt: str, errors: list[str], retry_count: int) -> str:  # noqa: ARG002
        return original_prompt

    def build_output(self, raw: Any, validation: ValidationResult, metadata: Any, *, context: Any = None) -> Any:  # noqa: ARG002
        return raw


class _ModeWithTools(_ModeNoTools):
    requires_tool_consultation = True


class _ModeNoEnrichmentWithTools(_ModeNoTools):
    """Modo de consistencia: sin enrichment de memoria pero con pre-consulta de tools."""

    requires_enrichment = False
    requires_tool_consultation = True


class _CountingEnricher:
    def __init__(self) -> None:
        self.calls = 0

    async def enrich(self, system_prompt: str, base: str, project_id: Any, *, phase: Any = None) -> str:  # noqa: ARG002
        self.calls += 1
        return system_prompt


def _make_loop(resolver: _CountingToolResolver) -> GenerationLoop:
    return GenerationLoop(
        llm_client=_StubLLM(),  # type: ignore[reportArgumentType]
        max_iterations=2,
        prompt_enricher=_StubEnricher(),  # type: ignore[reportArgumentType]
        tool_resolver=resolver,  # type: ignore[reportArgumentType]
        session_recorder=_StubRecorder(),  # type: ignore[reportArgumentType]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generation_loop_skips_tool_consultation_for_scratch_modes() -> None:
    # Arrange
    resolver = _CountingToolResolver()
    loop = _make_loop(resolver)

    # Act
    await loop.run(_ModeNoTools(), context={}, skill_name="test")

    # Assert — sin pre-consulta de tools
    assert resolver.calls == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generation_loop_consults_tools_when_mode_requires_it() -> None:
    # Arrange
    resolver = _CountingToolResolver()
    loop = _make_loop(resolver)

    # Act
    await loop.run(_ModeWithTools(), context={}, skill_name="test")

    # Assert
    assert resolver.calls == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generation_loop_consults_tools_without_enrichment() -> None:
    # Arrange — modo sin enrichment (consistencia) igual consulta tools de conocimiento
    resolver = _CountingToolResolver()
    enricher = _CountingEnricher()
    loop = GenerationLoop(
        llm_client=_StubLLM(),  # type: ignore[reportArgumentType]
        max_iterations=2,
        prompt_enricher=enricher,  # type: ignore[reportArgumentType]
        tool_resolver=resolver,  # type: ignore[reportArgumentType]
        session_recorder=_StubRecorder(),  # type: ignore[reportArgumentType]
    )

    # Act
    await loop.run(_ModeNoEnrichmentWithTools(), context={}, skill_name="test")

    # Assert
    assert resolver.calls == 1
    assert enricher.calls == 0


@pytest.mark.unit
def test_generation_modes_are_scratch_no_tools() -> None:
    # Arrange
    # Act & Assert — los modos de generación desde cero omiten la pre-consulta
    assert getattr(DiscoveryMode(), "requires_tool_consultation", True) is False
