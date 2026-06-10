from __future__ import annotations

import json

import pytest

from kosmo.application.orchestration.nodes.discovery_generator import (
    _build_discovery_prompt,
    _parse_discovery,
)
from kosmo.application.orchestration.nodes.ears_generator import _parse_ears
from kosmo.contracts.orchestration.graph_deps import GraphDependencies
from kosmo.contracts.sdd.discovery import DiscoveryDocument, RawIdea
from kosmo.contracts.sdd.state import (
    CritiqueRecord,
    KOSMOState,
)

_DISCOVERY_JSON = json.dumps(
    {
        "vision": "Una plataforma SaaS para gestion de inventarios en tiempo real.",
        "problem_space": "Las empresas pierden trazabilidad de su inventario usando hojas de calculo.",
        "actors": "Administradores de bodega, operarios, gerentes de operaciones.",
        "value_proposition": "Visibilidad total del inventario en tiempo real con alertas proactivas.",
        "use_cases": "Registrar entrada de producto, registrar salida, generar reporte de stock.",
        "core_capabilities": "CRUD de productos, dashboard de inventario, alertas de bajo stock.",
        "business_rules": "Solo administradores pueden ajustar inventario manualmente.",
        "quality_attributes": "Disponibilidad 99.9%, latencia < 200ms, escalabilidad horizontal.",
        "scope": "Incluye gestion de inventario y dashboard. No incluye facturacion ni ERP.",
    }
)

_EMPTY_DISCOVERY = json.dumps({"vision": ""})

_FEATURES_JSON = json.dumps(
    [
        {
            "title": "Gestion de inventario",
            "description": "Crear, editar, consultar y eliminar productos del inventario con validacion de stock.",
        },
        {
            "title": "Alertas de bajo stock",
            "description": "Notificar automaticamente cuando un producto alcanza el umbral minimo definido.",
        },
        {
            "title": "Reportes de movimiento",
            "description": "Generar reportes de entradas y salidas de productos por periodo y responsable.",
        },
    ]
)

_EARS_JSON = json.dumps(
    {
        "ubiquitous": [
            {
                "pattern": "ubiquitous",
                "trigger": None,
                "system": "El sistema",
                "response": "identifica de forma unica cada pedido mediante un numero de referencia",
                "acceptance_criteria": [
                    {
                        "description": "Cada pedido recibe un identificador unico al ser creado",
                        "scenario": "Dado que se crea un nuevo pedido, cuando el sistema lo registra, entonces el pedido recibe un numero de referencia unico",
                        "expected_result": "El pedido tiene un numero de referencia que no se repite en ningun otro pedido",
                        "verified_by": "prueba funcional",
                    }
                ],
                "source_statement": "The system shall identificar de forma unica cada pedido mediante un numero de referencia",
                "rationale": "La trazabilidad de cada pedido es esencial para operacion y servicio al cliente",
                "traceability": ["feature: auth"],
            }
        ],
        "event": [],
        "state": [],
        "optional": [],
        "unwanted": [],
        "complex": [],
    }
)


@pytest.mark.unit
class TestDiscoveryGenerator:
    async def test_requires_graph_deps(self, kosmo_state: KOSMOState) -> None:
        from kosmo.application.orchestration.nodes.discovery_generator import (
            discovery_generator_node,
        )

        result = await discovery_generator_node(kosmo_state)
        assert result["validation_status"] == "needs_revision"

    async def test_successful_generation(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.discovery_generator import (
            discovery_generator_node,
        )

        graph_deps.llm_client.set_response(_DISCOVERY_JSON)
        state = kosmo_state.model_copy(
            update={"graph_deps": graph_deps, "raw_idea": RawIdea(text="SaaS inventory")}
        )

        result = await discovery_generator_node(state)
        assert result["validation_status"] == "pending_review"
        assert isinstance(result["discovery"], DiscoveryDocument)
        assert result["discovery"].vision != ""

    async def test_empty_vision_rejected(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.discovery_generator import (
            discovery_generator_node,
        )

        graph_deps.llm_client.set_response(_EMPTY_DISCOVERY)
        state = kosmo_state.model_copy(
            update={"graph_deps": graph_deps, "raw_idea": RawIdea(text="idea")}
        )

        result = await discovery_generator_node(state)
        assert result["validation_status"] == "needs_revision"
        assert any("empty" in str(e).lower() for e in result.get("errors", []))

    async def test_llm_failure(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.discovery_generator import (
            discovery_generator_node,
        )

        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy(
            update={"graph_deps": graph_deps, "raw_idea": RawIdea(text="test")}
        )

        result = await discovery_generator_node(state)
        assert result["validation_status"] == "needs_revision"

    async def test_increments_generation_attempts(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.discovery_generator import (
            discovery_generator_node,
        )

        graph_deps.llm_client.set_response(_DISCOVERY_JSON)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "raw_idea": RawIdea(text="test"),
                "generation_attempts": 2,
            }
        )

        result = await discovery_generator_node(state)
        assert result["generation_attempts"] == 3

    async def test_consumes_critic_feedback(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.discovery_generator import (
            discovery_generator_node,
        )

        graph_deps.llm_client.set_response(_DISCOVERY_JSON)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "raw_idea": RawIdea(text="test"),
                "critique_log": [
                    CritiqueRecord(
                        agent_id="qc", severity="warning", message="Falta detalle en actores"
                    )
                ],
                "generation_attempts": 1,
            }
        )

        await discovery_generator_node(state)
        prompt = graph_deps.llm_client.last_prompt
        assert "Retroalimentacion del Critic" in prompt.user_prompt

    async def test_consumes_improve_instruction(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.discovery_generator import (
            discovery_generator_node,
        )

        graph_deps.llm_client.set_response(_DISCOVERY_JSON)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "raw_idea": RawIdea(text="test"),
                "shared_scratchpad": {"improve_instruction": "Agregar mas actores"},
            }
        )

        await discovery_generator_node(state)
        prompt = graph_deps.llm_client.last_prompt
        assert "Agregar mas actores" in prompt.user_prompt


@pytest.mark.unit
class TestFeaturesGenerator:
    async def test_generates_features(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.features_generator import features_generator_node

        graph_deps.llm_client.set_response(_FEATURES_JSON)
        state = kosmo_state.model_copy()

        result = await features_generator_node(state)
        assert result["validation_status"] == "pending_review"
        assert len(result["features"]) == 3
        assert result["features"][0].title == "Gestion de inventario"

    async def test_filters_duplicates(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.features_generator import features_generator_node
        from kosmo.contracts.sdd.feature import Feature, FeatureId

        graph_deps.llm_client.set_response(_FEATURES_JSON)
        existing = Feature(
            id=FeatureId("feat_existing"),
            project_id="prj_test01",
            title="Gestion de inventario",
            description="existing",
        )
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps, "features": [existing]})

        result = await features_generator_node(state)
        titles = [f.title for f in result["features"]]
        assert titles.count("Gestion de inventario") == 1

    async def test_empty_response_rejected(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.features_generator import features_generator_node

        graph_deps.llm_client.set_response("[]")
        state = kosmo_state.model_copy()

        result = await features_generator_node(state)
        assert result["validation_status"] == "needs_revision"

    async def test_llm_failure(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.features_generator import features_generator_node

        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy()

        result = await features_generator_node(state)
        assert result["validation_status"] == "needs_revision"

    async def test_critic_feedback_mode(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.features_generator import features_generator_node

        graph_deps.llm_client.set_response(_FEATURES_JSON)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "critique_log": [
                    CritiqueRecord(agent_id="qc", severity="blocker", message="Titulos muy vagos")
                ],
                "generation_attempts": 2,
            }
        )

        await features_generator_node(state)
        prompt = graph_deps.llm_client.last_prompt
        assert "Corrige" in prompt.user_prompt


@pytest.mark.unit
class TestEARSGenerator:
    async def test_generates_requirements(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)
        graph_deps.llm_client.set_response(_EARS_JSON)
        state = kosmo_state.model_copy()
        state.shared_scratchpad["current_feature_title"] = "Test Feature"
        state.shared_scratchpad["current_feature_description"] = "Test description"

        result = await ears_generator_node(state)
        assert result["validation_status"] == "approved"
        assert len(result["requirements"]) == 1
        assert result["requirements"][0].pattern == "ubiquitous"

    async def test_invalid_format_rejected(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)
        graph_deps.llm_client.set_response("not valid json [")
        state = kosmo_state.model_copy()

        result = await ears_generator_node(state)
        assert result["validation_status"] == "needs_revision"

    async def test_llm_failure(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)
        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy()

        result = await ears_generator_node(state)
        assert result["validation_status"] == "needs_revision"

    async def test_empty_result_rejected(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)

        graph_deps.llm_client.set_response(
            json.dumps(
                {
                    "ubiquitous": [],
                    "event": [],
                    "state": [],
                    "optional": [],
                    "unwanted": [],
                    "complex": [],
                }
            )
        )
        state = kosmo_state.model_copy()

        result = await ears_generator_node(state)
        assert result["validation_status"] == "needs_revision"

    async def test_business_terms_in_prompt(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)
        graph_deps.llm_client.set_response(_EARS_JSON)
        state = kosmo_state.model_copy()

        await ears_generator_node(state)
        prompt = graph_deps.llm_client.last_prompt
        assert "NEGOCIO" in prompt.system_prompt
        assert "API" in prompt.system_prompt or "PROHIBIDO" in prompt.system_prompt

    async def test_auto_repairs_leaks_in_response(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)

        leaky_json = json.dumps(
            {
                "ubiquitous": [
                    {
                        "pattern": "ubiquitous",
                        "trigger": None,
                        "system": "El sistema",
                        "response": "guardar datos",
                        "acceptance_criteria": [
                            {"description": "El endpoint guarda en PostgreSQL"}
                        ],
                        "source_statement": "The system shall guardar datos en la base de datos PostgreSQL.",
                        "traceability": ["feature: test"],
                    }
                ],
                "event": [],
                "state": [],
                "optional": [],
                "unwanted": [],
                "complex": [],
            }
        )
        graph_deps.llm_client.set_response(leaky_json)
        state = kosmo_state.model_copy()

        result = await ears_generator_node(state)
        req = result["requirements"][0]
        assert "PostgreSQL" not in req.source_statement
        assert "[comportamiento de negocio]" in req.source_statement

    async def test_acceptance_criteria_with_scenario(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)

        graph_deps.llm_client.set_response(_EARS_JSON)
        state = kosmo_state.model_copy()

        result = await ears_generator_node(state)
        req = result["requirements"][0]
        assert len(req.acceptance_criteria) > 0
        ac = req.acceptance_criteria[0]
        assert ac.scenario != ""
        assert ac.expected_result != ""
        assert ac.description != ""

    async def test_rationale_included(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)

        graph_deps.llm_client.set_response(_EARS_JSON)
        state = kosmo_state.model_copy()

        result = await ears_generator_node(state)
        req = result["requirements"][0]
        assert req.rationale != ""

    async def test_batch_score_stored_in_scratchpad(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.helpers import set_current_deps
        from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node

        set_current_deps(graph_deps)

        graph_deps.llm_client.set_response(_EARS_JSON)
        state = kosmo_state.model_copy()

        result = await ears_generator_node(state)
        scratchpad = result["shared_scratchpad"]
        assert "ears_batch_score" in scratchpad
        score = scratchpad["ears_batch_score"]
        assert score["total"] == 1
        assert score["overall_score"] >= 0


@pytest.mark.unit
class TestDraftRefiner:
    async def test_refines_content(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.draft_refiner import draft_refiner_node

        graph_deps.llm_client.set_response("# Refined content\n\nImproved version.")
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {
                    "current_draft": "Original draft",
                    "improve_instruction": "Make it better",
                },
            }
        )

        result = await draft_refiner_node(state)
        assert result["validation_status"] == "pending_review"
        assert "refined_content" in result["shared_scratchpad"]

    async def test_no_deps_fails(self, kosmo_state: KOSMOState) -> None:
        from kosmo.application.orchestration.nodes.draft_refiner import draft_refiner_node

        result = await draft_refiner_node(kosmo_state)
        assert result["validation_status"] == "needs_revision"

    async def test_llm_failure(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        from kosmo.application.orchestration.nodes.draft_refiner import draft_refiner_node

        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy()

        result = await draft_refiner_node(state)
        assert result["validation_status"] == "needs_revision"


@pytest.mark.unit
class TestDiscoveryParser:
    def test_parse_valid_discovery(self) -> None:
        result = _parse_discovery(_DISCOVERY_JSON)
        assert result is not None
        assert result.vision == "Una plataforma SaaS para gestion de inventarios en tiempo real."
        assert len(result.use_cases) > 0

    def test_parse_empty_json_returns_none(self) -> None:
        result = _parse_discovery("{}")
        assert result is not None
        assert result.vision == ""

    def test_parse_invalid_json_returns_none(self) -> None:
        result = _parse_discovery("not json at all")
        assert result is None

    def test_parse_list_uses_first_element(self) -> None:
        result = _parse_discovery(f"[{_DISCOVERY_JSON}]")
        assert result is not None
        assert "SaaS" in result.vision


@pytest.mark.unit
class TestEARSParser:
    def test_parse_valid_ears(self) -> None:
        data = json.loads(_EARS_JSON)
        result = _parse_ears(data)
        assert len(result) == 1
        assert result[0].pattern == "ubiquitous"

    def test_parse_empty_dict(self) -> None:
        result = _parse_ears({})
        assert result == []

    def test_parse_skips_invalid_items(self) -> None:
        data = {"ubiquitous": [{"not": "valid", "response": ""}], "event": []}
        result = _parse_ears(data)
        assert len(result) == 1


@pytest.mark.unit
class TestBuildDiscoveryPrompt:
    def test_includes_iteration(self) -> None:
        result = _build_discovery_prompt(3, "desc", {}, {}, "", "", False, "")
        assert "Iteracion 3" in result

    def test_includes_feedback(self) -> None:
        result = _build_discovery_prompt(2, "desc", {}, {}, "prev", "Add detail", False, "")
        assert "Add detail" in result

    def test_includes_context(self) -> None:
        result = _build_discovery_prompt(1, "desc", {"domain": "ecommerce"}, {}, "", "", False, "")
        assert "ecommerce" in result
