import pytest

from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.contracts.llm.ports import LLMResponse, PromptTemplate
from kosmo.contracts.pipeline.orchestrator_ports import Skill
from kosmo.contracts.pipeline.phase_contexts import DirectModificationContext
from kosmo.contracts.pipeline.phase_outputs import DirectModificationResult
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_modes.direct_modification_mode import DirectModificationMode
from kosmo.domain.pipeline.skill_registry import SkillRegistry

_DISCOVERY_MARKDOWN = (
    "## Visión del producto\n"
    "El producto ayuda a las familias a repartir gastos.\n\n"
    "## Público objetivo\n"
    "Familias numerosas.\n"
)

_MODIFIED_MARKDOWN = (
    "## Visión del producto\n"
    "El producto ayuda a las familias a repartir gastos.\n\n"
    "## Público objetivo\n"
    "Pequeñas y medianas empresas.\n"
)


class _StubModificationLLM:
    def __init__(self, responses: list[DirectModificationResult]) -> None:
        self._responses = responses
        self._calls: list[PromptTemplate] = []
        self._index = 0

    @property
    def call_count(self) -> int:
        return len(self._calls)

    @property
    def last_user_prompt(self) -> str:
        return self._calls[-1].user_prompt if self._calls else ""

    async def complete_typed[T](
        self,
        prompt: PromptTemplate,
        output_type: type[T],  # noqa: ARG002
        temperature: float = 0.1,  # noqa: ARG002
        max_tokens: int = 4096,  # noqa: ARG002
    ) -> T:
        self._calls.append(prompt)
        result = self._responses[self._index] if self._index < len(self._responses) else self._responses[-1]
        self._index += 1
        return result  # type: ignore[return-value]

    async def complete(self, prompt, temperature=0.3, max_tokens=4096):  # noqa: ARG002
        return LLMResponse(text="")

    async def complete_json(self, prompt, temperature=0.1, max_tokens=4096):  # noqa: ARG002
        return LLMResponse(text="{}")

    @property
    def supports_native_tools(self) -> bool:
        return False

    async def complete_with_tools(self, prompt, tools, tool_handler, temperature=0.1, max_tokens=2000):  # noqa: ARG002
        return ("", [])


def _make_agent(llm: _StubModificationLLM) -> KOSMOAgent:
    skill_reg = SkillRegistry()
    skill_reg.register(
        Skill(
            name="direct_modification",
            description="Modifica documentos directamente sin fase de plan",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=DirectModificationMode(),  # type: ignore[reportArgumentType]
        )
    )
    return KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        skill_registry=skill_reg,
    )


def _make_context(instruction: str = "Cambia el público objetivo a pymes") -> DirectModificationContext:
    return DirectModificationContext(
        current_document=_DISCOVERY_MARKDOWN,
        instruction=instruction,
        document_type=SpecPhase.DESCUBRIMIENTO,
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_direct_modification_applies_change() -> None:
    # Arrange
    expected = DirectModificationResult(
        applied=True,
        modified_document=_MODIFIED_MARKDOWN,
        modified_section="Público objetivo",
        change_description="Se cambió el público objetivo",
    )
    llm = _StubModificationLLM([expected])
    agent = _make_agent(llm)

    # Act
    result = await agent.execute_direct_modification(
        skill_name="direct_modification",
        context=_make_context(),
    )

    # Assert
    assert result.applied is True
    assert result.modified_document == _MODIFIED_MARKDOWN
    assert result.modified_section == "Público objetivo"
    assert llm.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_direct_modification_returns_clarification() -> None:
    # Arrange
    clarification = DirectModificationResult(
        applied=False,
        clarification_message="Por favor, especifica la sección y el cambio deseado",
    )
    llm = _StubModificationLLM([clarification])
    agent = _make_agent(llm)

    # Act
    result = await agent.execute_direct_modification(
        skill_name="direct_modification",
        context=_make_context(instruction="Cambia eso"),
    )

    # Assert
    assert result.applied is False
    assert "especifica" in result.clarification_message
    assert result.modified_document == ""


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_direct_modification_includes_session_history() -> None:
    # Arrange
    from kosmo.contracts.ai.chat import ChatRole, MensajeChat
    from kosmo.contracts.sdd.ids import ChatMessageId

    expected = DirectModificationResult(
        applied=True,
        modified_document=_MODIFIED_MARKDOWN,
        modified_section="Público objetivo",
    )
    llm = _StubModificationLLM([expected])
    agent = _make_agent(llm)

    history = [
        MensajeChat(
            id=ChatMessageId("chat_01"),
            role=ChatRole.USER,
            content="Cambia el público objetivo a pymes",
        ),
        MensajeChat(
            id=ChatMessageId("chat_02"),
            role=ChatRole.ASSISTANT,
            content="Apliqué el cambio de público objetivo.",
        ),
    ]

    # Act
    await agent.execute_direct_modification(
        skill_name="direct_modification",
        context=_make_context(instruction="Ahora cambia la propuesta de valor"),
        history=history,
    )

    # Assert
    assert "público objetivo a pymes" in llm.last_user_prompt
    assert "propuesta de valor" in llm.last_user_prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_direct_modification_raises_when_skill_not_found() -> None:
    # Arrange
    llm = _StubModificationLLM([])
    agent = _make_agent(llm)

    # Act & Assert
    with pytest.raises(ValueError, match="Skill "):
        await agent.execute_direct_modification(
            skill_name="nonexistent",
            context=_make_context(),
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_direct_modification_raises_without_skill_registry() -> None:
    # Arrange
    llm = _StubModificationLLM([])
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
    )

    # Act & Assert
    with pytest.raises(ValueError, match="SkillRegistry"):
        await agent.execute_direct_modification(
            skill_name="direct_modification",
            context=_make_context(),
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_direct_modification_retries_on_invalid_output() -> None:
    # Arrange
    invalid = DirectModificationResult(applied=True, modified_document="")
    valid = DirectModificationResult(
        applied=True,
        modified_document=_MODIFIED_MARKDOWN,
        modified_section="Público objetivo",
    )
    llm = _StubModificationLLM([invalid, valid])
    agent = _make_agent(llm)

    # Act
    result = await agent.execute_direct_modification(
        skill_name="direct_modification",
        context=_make_context(),
    )

    # Assert
    assert result.applied is True
    assert result.modified_document == _MODIFIED_MARKDOWN
    assert llm.call_count == 2
