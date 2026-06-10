from __future__ import annotations

import json

import pytest

from kosmo.application.orchestration.nodes.critic_evaluator import (
    _handle_approved,
    _handle_blocked,
    _handle_warnings,
    critic_evaluator_node,
)
from kosmo.application.orchestration.nodes.critics import (
    _determine_verdict,
    _parse_critic,
    consistency_critic_node,
    quality_critic_node,
    style_critic_node,
)
from kosmo.contracts.orchestration.graph_deps import GraphDependencies
from kosmo.contracts.sdd.feature import Feature, FeatureId
from kosmo.contracts.sdd.state import (
    CritiqueRecord,
    KOSMOState,
)

_QUALITY_OK = json.dumps({"severity": "none", "message": "Todo bien"})
_QUALITY_BLOCKER = json.dumps({"severity": "blocker", "message": "Contenido incompleto"})
_QUALITY_WARNING = json.dumps({"severity": "warning", "message": "Poco detalle"})
_STYLE_OK = json.dumps({"severity": "none", "message": "Estilo correcto"})
_CONSISTENCY_OK = json.dumps({"severity": "none", "message": "Sin duplicados"})
_CONSISTENCY_DUP = json.dumps(
    {"severity": "blocker", "message": "Duplicado: Gestion de inventario"}
)


@pytest.mark.unit
class TestQualityCritic:
    async def test_no_content_returns_blocker(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await quality_critic_node(state)
        critiques = result["critique_log"]
        assert len(critiques) == 1
        assert critiques[0].severity == "blocker"
        assert "No hay contenido" in critiques[0].message

    async def test_no_deps_skips(self, kosmo_state: KOSMOState) -> None:
        result = await quality_critic_node(kosmo_state)
        assert result["validation_status"] == "needs_revision"

    async def test_llm_failure_skips_with_warning(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "some content"},
            }
        )
        result = await quality_critic_node(state)
        assert result["validation_status"] == "approved"
        assert result["critique_log"][0].severity == "warning"

    async def test_approves_good_content(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_QUALITY_OK)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "Good content"},
            }
        )
        result = await quality_critic_node(state)
        assert result["validation_status"] == "approved"

    async def test_flags_poor_content(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_QUALITY_BLOCKER)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "bad"},
            }
        )
        result = await quality_critic_node(state)
        assert result["validation_status"] == "needs_revision"


@pytest.mark.unit
class TestStyleCritic:
    async def test_no_preferences_skips_approved(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await style_critic_node(state)
        assert result["validation_status"] == "approved"
        assert "Sin preferencias" in result["critique_log"][0].message

    async def test_no_deps_skips(self, kosmo_state: KOSMOState) -> None:
        result = await style_critic_node(kosmo_state)
        assert result["validation_status"] == "needs_revision"

    async def test_llm_failure_skips_with_warning(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {
                    "generated_document_md": "content",
                    "preference_retriever_output": {
                        "preferences_prompt": "Prefiere listas numeradas"
                    },
                },
            }
        )
        result = await style_critic_node(state)
        assert result["validation_status"] == "approved"
        assert result["critique_log"][0].severity == "warning"

    async def test_with_preferences_evaluates(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_STYLE_OK)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {
                    "generated_document_md": "content",
                    "preference_retriever_output": {
                        "preferences_prompt": "Prefiere verbos en imperativo"
                    },
                },
            }
        )
        result = await style_critic_node(state)
        assert result["validation_status"] == "approved"


@pytest.mark.unit
class TestConsistencyCritic:
    async def test_no_deps_skips(self, kosmo_state: KOSMOState) -> None:
        result = await consistency_critic_node(kosmo_state)
        assert result["validation_status"] == "needs_revision"

    async def test_llm_failure_skips_with_warning(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "content"},
            }
        )
        result = await consistency_critic_node(state)
        assert result["validation_status"] == "approved"

    async def test_no_existing_features_ok(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_CONSISTENCY_OK)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "content"},
            }
        )
        result = await consistency_critic_node(state)
        assert result["validation_status"] == "approved"

    async def test_detects_duplicates(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_CONSISTENCY_DUP)
        features = [
            Feature(
                id=FeatureId("feat_01"),
                project_id="prj_test01",
                title="Gestion de inventario",
                description="existing",
            )
        ]
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "features": features,
                "shared_scratchpad": {"generated_document_md": "content"},
            }
        )
        result = await consistency_critic_node(state)
        assert result["validation_status"] == "needs_revision"


@pytest.mark.unit
class TestCriticEvaluator:
    async def test_blocked_returns_needs_revision(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "critique_log": [
                    CritiqueRecord(agent_id="qc", severity="blocker", message="Fatal"),
                ],
            }
        )
        result = await critic_evaluator_node(state)
        assert result["critic_verdict"] == "needs_revision"
        assert result["validation_status"] == "needs_revision"

    async def test_warnings_within_limit_retries(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "critique_log": [
                    CritiqueRecord(agent_id="qc", severity="warning", message="Mejorable"),
                ],
                "critic_iteration": 0,
                "max_critic_iterations": 3,
            }
        )
        result = await critic_evaluator_node(state)
        assert result["critic_verdict"] == "needs_revision"

    async def test_approved_resets_iteration(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "critique_log": [
                    CritiqueRecord(agent_id="qc", severity="none", message="OK"),
                ],
                "critic_iteration": 2,
            }
        )
        result = await critic_evaluator_node(state)
        assert result["critic_verdict"] == "approved"
        assert result["critic_iteration"] == 0
        assert result["validation_status"] == "approved"

    async def test_exceeds_max_critic_iterations_approves(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "critique_log": [
                    CritiqueRecord(agent_id="qc", severity="warning", message="Mejorable"),
                ],
                "critic_iteration": 3,
                "max_critic_iterations": 3,
            }
        )
        result = await critic_evaluator_node(state)
        assert result["critic_verdict"] == "approved"

    async def test_empty_critique_log_approves(self, kosmo_state: KOSMOState) -> None:
        result = await critic_evaluator_node(kosmo_state)
        assert result["critic_verdict"] == "approved"


@pytest.mark.unit
class TestHandleBlocked:
    def test_records_blocker_in_history(self) -> None:
        blocked = [CritiqueRecord(agent_id="qc", severity="blocker", message="Fatal")]
        result = _handle_blocked(blocked, 1, [])
        assert result["critic_verdict"] == "needs_revision"
        assert len(result["tool_call_history"]) == 1
        assert result["tool_call_history"][0].params["verdict"] == "blocked"


@pytest.mark.unit
class TestHandleWarnings:
    def test_records_warning_in_history(self) -> None:
        warnings = [CritiqueRecord(agent_id="qc", severity="warning", message="Mejorable")]
        result = _handle_warnings(warnings, 2, [])
        assert result["critic_verdict"] == "needs_revision"
        assert len(result["tool_call_history"]) == 1


@pytest.mark.unit
class TestHandleApproved:
    def test_records_approval_in_history(self) -> None:
        result = _handle_approved([])
        assert result["critic_verdict"] == "approved"
        assert result["critic_iteration"] == 0
        assert len(result["tool_call_history"]) == 1
        assert result["tool_call_history"][0].params["verdict"] == "approved"


@pytest.mark.unit
class TestParseCritic:
    def test_parse_valid_json(self) -> None:
        result = _parse_critic('{"severity": "none", "message": "OK"}')
        assert result["severity"] == "none"

    def test_parse_list_returns_first(self) -> None:
        result = _parse_critic('[{"severity": "blocker"}]')
        assert result["severity"] == "blocker"

    def test_parse_invalid_returns_empty(self) -> None:
        result = _parse_critic("not json")
        assert result == {}


@pytest.mark.unit
class TestDetermineVerdict:
    def test_blocker_is_needs_revision(self) -> None:
        assert _determine_verdict({"severity": "blocker"}) == "needs_revision"

    def test_warning_is_needs_revision(self) -> None:
        assert _determine_verdict({"severity": "warning"}) == "needs_revision"

    def test_none_is_approved(self) -> None:
        assert _determine_verdict({"severity": "none"}) == "approved"

    def test_missing_severity_defaults_approved(self) -> None:
        assert _determine_verdict({}) == "approved"
