from __future__ import annotations

import pytest

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.agents.learning.nodes import (
    conflict_resolver,
    delta_extractor,
    preference_store,
)
from kosmo.domain.agents.memory_agent.nodes import injection_preparer


@pytest.mark.unit
class TestDeltaExtractor:
    def test_identical_docs_zero_diff(self) -> None:
        doc = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hola"}]}],
        }
        result = delta_extractor(doc, doc)
        assert result["added_lines"] == 0
        assert result["removed_lines"] == 0

    def test_detects_additions(self) -> None:
        original = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "A"}]}],
        }
        corrected = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "A"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "B"}]},
            ],
        }
        result = delta_extractor(original, corrected)
        assert result["added_lines"] > 0

    def test_detects_removals(self) -> None:
        original = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "A"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "B"}]},
            ],
        }
        corrected = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "A"}]}],
        }
        result = delta_extractor(original, corrected)
        assert result["removed_lines"] > 0

    def test_detects_modifications(self) -> None:
        original = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hola"}]}],
        }
        corrected = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Adios"}]}],
        }
        result = delta_extractor(original, corrected)
        assert result["added_lines"] >= 1
        assert result["removed_lines"] >= 1

    def test_includes_diff_text(self) -> None:
        original = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Original"}]}],
        }
        corrected = {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Corrected"}]}],
        }
        result = delta_extractor(original, corrected)
        assert "diff_text" in result
        assert len(result["diff_text"]) > 0


@pytest.mark.unit
class TestInjectionPreparer:
    def test_empty_prefs(self) -> None:
        result = injection_preparer([])
        assert result == ""

    def test_formats_preferences(self) -> None:
        prefs = [
            UserPreference(
                id="p1",
                user_id="u1",
                document_type="discovery",
                rule_text="Prefiere listas numeradas",
            ),
            UserPreference(
                id="p2",
                user_id="u1",
                document_type="discovery",
                rule_text="Evita jerga tecnica",
            ),
        ]
        result = injection_preparer(prefs)
        assert "1." in result
        assert "2." in result
        assert "Prefiere listas" in result
        assert "Evita jerga" in result

    def test_includes_conflict_guidance(self) -> None:
        prefs = [
            UserPreference(
                id="p1",
                user_id="u1",
                document_type="discovery",
                rule_text="Test rule",
            ),
        ]
        result = injection_preparer(prefs)
        assert "conflicto" in result.lower()
        assert "reciente" in result.lower()


@pytest.mark.unit
class TestConflictResolver:
    async def test_filters_duplicates(self, in_memory_preference_repo) -> None:
        existing = UserPreference(
            id="ep1",
            user_id="usr_test01",
            project_id="prj_test01",
            document_type="discovery",
            rule_text="Usa listas numeradas",
        )
        await in_memory_preference_repo.add(existing)

        new_rules = [{"rule_text": "Usa listas numeradas", "corpus": ["list"]}]
        result = await conflict_resolver(
            new_rules, "usr_test01", ProjectId("prj_test01"), in_memory_preference_repo
        )
        assert result[0].get("duplicate") is True

    async def test_passes_new_rules(self, in_memory_preference_repo) -> None:
        new_rules = [{"rule_text": "Nueva regla unica", "corpus": ["unique"]}]
        result = await conflict_resolver(
            new_rules, "usr_test01", ProjectId("prj_test01"), in_memory_preference_repo
        )
        assert result[0].get("duplicate") is not True


@pytest.mark.unit
class TestPreferenceStore:
    async def test_creates_with_correct_metadata(self, in_memory_preference_repo) -> None:
        rules = [{"rule_text": "Test rule", "corpus": ["test"], "context_snippet": "ctx"}]
        result = await preference_store(
            rules, "usr_test01", ProjectId("prj_test01"), "discovery", in_memory_preference_repo
        )
        assert len(result) == 1
        assert result[0].user_id == "usr_test01"
        assert result[0].project_id == "prj_test01"
        assert result[0].document_type == "discovery"

    async def test_generates_prefixed_ids(self, in_memory_preference_repo) -> None:
        rules = [{"rule_text": "Test rule", "corpus": [], "context_snippet": ""}]
        result = await preference_store(
            rules, "usr_test01", ProjectId("prj_test01"), "discovery", in_memory_preference_repo
        )
        assert result[0].id.startswith("pref_")


@pytest.mark.unit
class TestLearnFromCorrectionNode:
    async def test_no_correction_data_skips(self, kosmo_state) -> None:
        from kosmo.application.orchestration.nodes.learn_from_correction import (
            learn_from_correction_node,
        )

        result = await learn_from_correction_node(kosmo_state)
        assert "tool_call_history" in result

    async def test_with_correction_data_invokes_learning(self, graph_deps, kosmo_state) -> None:
        from kosmo.application.orchestration.nodes.learn_from_correction import (
            learn_from_correction_node,
        )

        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {
                    "correction_original": "original content",
                    "correction_corrected": "corrected content",
                    "correction_document_type": "discovery",
                },
            }
        )
        result = await learn_from_correction_node(state)
        records = result.get("tool_call_history", [])
        assert any(r.tool_name == "learn_from_correction" for r in records)

    async def test_fallback_to_generated_content(self, graph_deps, kosmo_state) -> None:
        from kosmo.application.orchestration.nodes.learn_from_correction import (
            learn_from_correction_node,
        )

        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "output_ready": True,
                "shared_scratchpad": {
                    "generated_document_md": "generated content",
                    "correction_corrected": "corrected content",
                },
            }
        )
        result = await learn_from_correction_node(state)
        records = result.get("tool_call_history", [])
        assert any(r.tool_name == "learn_from_correction" for r in records)
