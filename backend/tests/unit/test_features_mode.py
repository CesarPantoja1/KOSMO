import json

import pytest

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.pipeline.phase_contexts import FeaturesPhaseContext, SuggestFeaturesContext
from kosmo.contracts.pipeline.phase_outputs import (
    FeaturesPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import (
    DocumentNode,
    RichTextDocument,
    SectionHeading,
    SpecPhase,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.pipeline.phase_modes.features_mode import FeaturesMode


def _a_discovery_document() -> RichTextDocument:
    return RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Vision del producto", level=2, slug="vision"),
                content="El producto ayuda a las familias a organizar gastos compartidos.",
            ),
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Metas del producto", level=2, slug="metas"),
                content="1. Gestion financiera de gastos.",
            ),
        ]
    )


def _a_valid_features_json() -> str:
    return json.dumps(
        {
            "features": [
                {
                    "number": 1,
                    "title": "Registrar gastos entre participantes",
                    "description": (
                        "Cualquier participante del grupo indica el monto de un gasto, "
                        "selecciona a las personas involucradas y elige como repartirlo."
                    ),
                    "origin": (
                        "Se deriva de la meta Gestion financiera de gastos. "
                        "Se traza a Metas del producto, Actores y Reglas de negocio."
                    ),
                }
            ]
        }
    )


# ------------------------------------------------------------------
# system_prompt
# ------------------------------------------------------------------


@pytest.mark.unit
def test_features_mode_system_prompt_mentions_four_fields() -> None:
    # Arrange
    mode = FeaturesMode()

    # Act
    prompt = mode.system_prompt

    # Assert
    assert "Codigo" in prompt or "Código" in prompt
    assert "Titulo" in prompt or "Título" in prompt
    assert "Descripcion" in prompt or "Descripción" in prompt
    assert "Origen" in prompt


@pytest.mark.unit
def test_features_mode_system_prompt_lists_discovery_sections_for_traceability() -> None:
    # Arrange
    mode = FeaturesMode()

    # Act
    prompt = mode.system_prompt

    # Assert
    assert "Metas del producto" in prompt
    assert "Reglas de negocio" in prompt


# ------------------------------------------------------------------
# phase_name
# ------------------------------------------------------------------


@pytest.mark.unit
def test_features_mode_phase_name_is_caracteristicas() -> None:
    # Arrange
    mode = FeaturesMode()

    # Act
    phase = mode.phase_name

    # Assert
    assert phase == SpecPhase.CARACTERISTICAS


# ------------------------------------------------------------------
# build_user_prompt
# ------------------------------------------------------------------


@pytest.mark.unit
def test_features_mode_build_user_prompt_includes_discovery_document() -> None:
    # Arrange
    mode = FeaturesMode()
    context = FeaturesPhaseContext(
        discovery_document=_a_discovery_document(),
        project_id=ProjectId("prj_test"),
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "Vision del producto" in prompt
    assert "organizar gastos compartidos" in prompt


@pytest.mark.unit
def test_features_mode_build_user_prompt_includes_existing_titles() -> None:
    # Arrange
    mode = FeaturesMode()
    context = FeaturesPhaseContext(
        discovery_document=_a_discovery_document(),
        project_id=ProjectId("prj_test"),
        existing_feature_titles=["Consultar balances"],
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "Consultar balances" in prompt


@pytest.mark.unit
def test_features_mode_build_user_prompt_includes_preferences() -> None:
    # Arrange
    mode = FeaturesMode()
    context = FeaturesPhaseContext(
        discovery_document=_a_discovery_document(),
        project_id=ProjectId("prj_test"),
        user_preferences=[
            UserPreference(id="pref_1", user_id="usr_1", rule_text="Usar lenguaje formal"),
        ],
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "Usar lenguaje formal" in prompt


@pytest.mark.unit
def test_features_mode_build_user_prompt_with_suggest_context() -> None:
    # Arrange
    mode = FeaturesMode()
    context = SuggestFeaturesContext(
        discovery_document=_a_discovery_document(),
        existing_feature_titles=["Feature existente"],
        next_feature_number=3,
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "Feature existente" in prompt


@pytest.mark.unit
def test_features_mode_build_user_prompt_includes_five_count_on_first_generation() -> None:
    # Arrange
    mode = FeaturesMode()
    context = FeaturesPhaseContext(
        discovery_document=_a_discovery_document(),
        project_id=ProjectId("prj_test"),
        existing_feature_titles=[],
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "5" in prompt
    assert "EXACTAMENTE" in prompt


@pytest.mark.unit
def test_features_mode_build_user_prompt_omits_five_count_on_subsequent_generation() -> None:
    # Arrange
    mode = FeaturesMode()
    context = FeaturesPhaseContext(
        discovery_document=_a_discovery_document(),
        project_id=ProjectId("prj_test"),
        existing_feature_titles=["Feature ya existente"],
    )

    # Act
    prompt = mode.build_user_prompt(context)

    # Assert
    assert "EXACTAMENTE 5" not in prompt


# ------------------------------------------------------------------
# validate_output
# ------------------------------------------------------------------


@pytest.mark.unit
def test_features_mode_validate_output_accepts_four_field_format() -> None:
    # Arrange
    mode = FeaturesMode()
    mode._existing_titles = ["Caracteristica existente"]  # type: ignore[reportPrivateUsage]
    raw = json.loads(_a_valid_features_json())

    # Act
    result = mode.validate_output(raw)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


@pytest.mark.unit
def test_features_mode_validate_output_accepts_raw_text_json() -> None:
    # Arrange
    mode = FeaturesMode()
    mode._existing_titles = ["Caracteristica existente"]  # type: ignore[reportPrivateUsage]
    output: dict[str, str] = {"raw_text": _a_valid_features_json()}

    # Act
    result = mode.validate_output(output)

    # Assert
    assert result.is_valid is True


@pytest.mark.unit
def test_features_mode_validate_output_rejects_technical_term() -> None:
    # Arrange
    mode = FeaturesMode()
    raw = {
        "features": [
            {
                "number": 1,
                "title": "Gestionar con API del grupo",
                "description": "El usuario interactua con la API para registrar gastos.",
                "origin": "Se traza a Metas del producto.",
            }
        ]
    }

    # Act
    result = mode.validate_output(raw)

    # Assert
    assert result.is_valid is False
    assert any("API" in e for e in result.errors)


@pytest.mark.unit
def test_features_mode_validate_output_rejects_unrecognized_format() -> None:
    # Arrange
    mode = FeaturesMode()

    # Act
    result = mode.validate_output(12345)

    # Assert
    assert result.is_valid is False


# ------------------------------------------------------------------
# validate_output — first generation count enforcement
# ------------------------------------------------------------------


@pytest.mark.unit
def test_features_mode_validate_output_accepts_five_features_on_first_generation() -> None:
    # Arrange
    mode = FeaturesMode()
    raw = {
        "features": [
            {
                "number": 1,
                "title": "Registrar gastos compartidos",
                "description": (
                    "Cualquier participante indica el monto de un gasto y selecciona a las personas involucradas."
                ),
                "origin": "Se traza a Metas del producto.",
            },
            {
                "number": 2,
                "title": "Consultar balances pendientes",
                "description": "Cada miembro accede a un resumen donde visualiza cuanto debe y cuanto le deben.",
                "origin": "Se traza a Metas del producto.",
            },
            {
                "number": 3,
                "title": "Liquidar deudas del grupo",
                "description": (
                    "El administrador visualiza un plan de transferencias para saldar todas las cuentas pendientes."
                ),
                "origin": "Se traza a Reglas de negocio.",
            },
            {
                "number": 4,
                "title": "Administrar participantes del hogar",
                "description": "El administrador invita o remueve miembros y asigna roles dentro del grupo familiar.",
                "origin": "Se traza a Actores.",
            },
            {
                "number": 5,
                "title": "Notificar recordatorios de pago",
                "description": (
                    "Los miembros reciben avisos automaticos cuando se acerca la fecha de vencimiento de una deuda."
                ),
                "origin": "Se traza a Alcance.",
            },
        ]
    }

    # Act
    result = mode.validate_output(raw)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


@pytest.mark.unit
def test_features_mode_validate_output_rejects_wrong_count_on_first_generation() -> None:
    # Arrange
    mode = FeaturesMode()
    raw = {
        "features": [
            {
                "number": 1,
                "title": "Registrar gastos compartidos",
                "description": (
                    "Cualquier participante indica el monto de un gasto y selecciona a las personas involucradas."
                ),
                "origin": "Se traza a Metas del producto.",
            },
            {
                "number": 2,
                "title": "Consultar balances pendientes",
                "description": "Cada miembro accede a un resumen donde visualiza cuanto debe y cuanto le deben.",
                "origin": "Se traza a Metas del producto.",
            },
            {
                "number": 3,
                "title": "Liquidar deudas del grupo",
                "description": (
                    "El administrador visualiza un plan de transferencias para saldar todas las cuentas pendientes."
                ),
                "origin": "Se traza a Reglas de negocio.",
            },
        ]
    }

    # Act
    result = mode.validate_output(raw)

    # Assert
    assert result.is_valid is False
    assert any("5" in e and "3" in e for e in result.errors)


@pytest.mark.unit
def test_features_mode_validate_output_skips_count_check_on_subsequent_generation() -> None:
    # Arrange
    mode = FeaturesMode()
    mode._existing_titles = ["Feature existente"]  # type: ignore[reportPrivateUsage]
    raw = json.loads(_a_valid_features_json())

    # Act
    result = mode.validate_output(raw)

    # Assert
    assert result.is_valid is True


# ------------------------------------------------------------------
# build_output
# ------------------------------------------------------------------


@pytest.mark.unit
def test_features_mode_build_output_returns_features_phase_output() -> None:
    # Arrange
    mode = FeaturesMode()
    mode._project_id = ProjectId("prj_test")  # type: ignore[reportPrivateUsage]
    raw = json.loads(_a_valid_features_json())
    metadata = GenerationMetadata(llm_calls=1)
    validation = ValidationResult(is_valid=True)

    # Act
    result = mode.build_output(raw, validation, metadata)

    # Assert
    assert isinstance(result, FeaturesPhaseOutput)
    assert len(result.features) == 1
    assert result.features[0].title == "Registrar gastos entre participantes"
    assert result.features[0].origin != ""
    assert "Metas del producto" in result.features[0].origin


@pytest.mark.unit
def test_features_mode_build_output_generates_feature_id() -> None:
    # Arrange
    mode = FeaturesMode()
    mode._project_id = ProjectId("prj_test")  # type: ignore[reportPrivateUsage]
    raw = json.loads(_a_valid_features_json())
    metadata = GenerationMetadata(llm_calls=1)
    validation = ValidationResult(is_valid=True)

    # Act
    result = mode.build_output(raw, validation, metadata)

    # Assert
    assert str(result.features[0].id).startswith("feat_")


@pytest.mark.unit
def test_features_mode_build_output_assigns_display_id_from_number() -> None:
    # Arrange
    mode = FeaturesMode()
    mode._project_id = ProjectId("prj_test")  # type: ignore[reportPrivateUsage]
    raw = json.loads(_a_valid_features_json())
    metadata = GenerationMetadata(llm_calls=1)
    validation = ValidationResult(is_valid=True)

    # Act
    result = mode.build_output(raw, validation, metadata)

    # Assert
    assert result.features[0].display_id == "C01"


# ------------------------------------------------------------------
# build_retry_prompt
# ------------------------------------------------------------------


@pytest.mark.unit
def test_features_mode_build_retry_prompt_appends_errors() -> None:
    # Arrange
    mode = FeaturesMode()

    # Act
    retry = mode.build_retry_prompt(
        original_prompt="PROMPT BASE",
        errors=["El titulo excede seis palabras"],
        retry_count=2,
    )

    # Assert
    assert "PROMPT BASE" in retry
    assert "intento 2" in retry
    assert "El titulo excede seis palabras" in retry


# ------------------------------------------------------------------
# available_tools
# ------------------------------------------------------------------


@pytest.mark.unit
def test_features_mode_available_tools_has_structure_validator() -> None:
    # Arrange
    mode = FeaturesMode()

    # Act
    tools = mode.available_tools

    # Assert
    assert any(t.name == "validate_feature_structure" for t in tools)
