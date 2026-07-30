import pytest

from kosmo.application.chat.validate_phase_context import (
    PhaseClassification,
    ValidatePhaseContextInput,
    ValidatePhaseContextUseCase,
)
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.document import SpecPhase


class _FakeClassifierClient:
    def __init__(self, result: PhaseClassification | Exception | None = None) -> None:
        self._result: PhaseClassification | Exception = result or PhaseClassification(
            belongs_to_current_phase=True,
        )
        self.calls: list[tuple] = []

    async def complete_typed[T](
        self,
        prompt: PromptTemplate,
        output_type: type[T],
        temperature: float = 0.1,
        max_tokens: int = 256,
    ) -> T:  # noqa: ARG002
        self.calls.append((prompt.system_prompt, prompt.user_prompt, temperature, max_tokens))
        if isinstance(self._result, Exception):
            raise self._result
        return self._result  # type: ignore[return-value]

    async def complete(self, prompt, temperature=0.3, max_tokens=4096):  # noqa: ARG002
        return None

    async def complete_json(self, prompt, temperature=0.1, max_tokens=4096):  # noqa: ARG002
        return None

    @property
    def supports_native_tools(self) -> bool:
        return False

    async def complete_with_tools(self, prompt, tools, tool_handler, temperature=0.1, max_tokens=2000):  # noqa: ARG002
        return ("", [])


def _make_use_case(llm_client: _FakeClassifierClient) -> ValidatePhaseContextUseCase:
    return ValidatePhaseContextUseCase(llm_client=llm_client)  # type: ignore[reportArgumentType]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_valid_message_belongs_to_current_phase() -> None:
    # Arrange
    result = PhaseClassification(belongs_to_current_phase=True, target_phase="", message="")
    client = _FakeClassifierClient(result)
    uc = _make_use_case(client)
    input_data = ValidatePhaseContextInput(
        content="Cambia el titulo de esta caracteristica a Recepcion de inventario",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is True
    assert output.redirect_message is None
    assert output.target_phase is None
    assert len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redirect_to_discovery_from_features() -> None:
    # Arrange
    result = PhaseClassification(
        belongs_to_current_phase=False,
        target_phase="discovery",
        message="Este cambio pertenece a la fase de Descubrimiento. Ve a esa fase para realizarlo.",
    )
    client = _FakeClassifierClient(result)
    uc = _make_use_case(client)
    input_data = ValidatePhaseContextInput(
        content="Quiero cambiar la Vision del negocio a B2B",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is False
    msg = "Este cambio pertenece a la fase de Descubrimiento. Ve a esa fase para realizarlo."
    assert output.redirect_message == msg
    assert output.target_phase == "descubrimiento"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redirect_to_requirements_from_features() -> None:
    # Arrange
    result = PhaseClassification(
        belongs_to_current_phase=False,
        target_phase="requirements",
        message="Este cambio pertenece a la fase de Requisitos. Ve a esa fase para realizarlo.",
    )
    client = _FakeClassifierClient(result)
    uc = _make_use_case(client)
    input_data = ValidatePhaseContextInput(
        content="Agrega un criterio de aceptacion para timeout en Dado-Cuando-Entonces",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is False
    assert output.target_phase == "requisitos"
    assert "Requisitos" in (output.redirect_message or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_llm_error_falls_back_to_valid() -> None:
    # Arrange
    client = _FakeClassifierClient(RuntimeError("LLM timeout"))
    uc = _make_use_case(client)
    input_data = ValidatePhaseContextInput(
        content="Hola",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_empty_message_returns_valid() -> None:
    # Arrange
    result = PhaseClassification(belongs_to_current_phase=False, target_phase="discovery", message="redirigir")
    client = _FakeClassifierClient(result)
    uc = _make_use_case(client)
    input_data = ValidatePhaseContextInput(
        content="   ",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is True
    assert len(client.calls) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_same_phase_in_target_treated_as_valid() -> None:
    # Arrange
    result = PhaseClassification(
        belongs_to_current_phase=True,
        target_phase="features",
        message="",
    )
    client = _FakeClassifierClient(result)
    uc = _make_use_case(client)
    input_data = ValidatePhaseContextInput(
        content="Necesito ayuda con el titulo de C01",
        current_phase=SpecPhase.CARACTERISTICAS,
    )

    # Act
    output = await uc.execute(input_data)

    # Assert
    assert output.is_valid is True
