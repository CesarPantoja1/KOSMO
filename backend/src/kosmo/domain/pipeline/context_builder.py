from __future__ import annotations

import re

from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryChatContext,
    DiscoveryRefinePhaseContext,
    FeatureChatContext,
    RequirementChatContext,
)
from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
from kosmo.contracts.sdd.document import AcceptanceCriterion
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, RequirementId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)

_req_header_re = re.compile(r"^###\s+(REQ-\d+\.\d+)\s+(.*)$", re.MULTILINE)
_req_pattern_re = re.compile(
    r"\*\*(Ubicuo|Basado en eventos|Determinado por estado"
    r"|Opcional|Comportamiento no deseado|Complejo)\*\*"
)
_ac_scenario_re = re.compile(r"\*\*Escenario:\s+(.+)\*\*")
_ac_given_re = re.compile(r"-\s+\*\*Dado\*\*\s+que\s+(.+)")
_ac_when_re = re.compile(r"-\s+\*\*Cuando\*\*\s+(.+)")
_ac_then_re = re.compile(r"-\s+\*\*Entonces\*\*\s+(.+)")


class ContextBuilder:
    def __init__(
        self,
        document_repo: DocumentRepository,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository | None = None,
        requirement_repo: RequirementRepository | None = None,
    ) -> None:
        self._document_repo = document_repo
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo

    async def build_discovery_refine_context(
        self,
        project_id: ProjectId,
        user_instructions: str,
    ) -> DiscoveryRefinePhaseContext:
        current_document = await self._document_repo.get_discovery(project_id)
        if current_document is None:
            raise PhaseTransitionError(
                detail="No existe un documento de descubrimiento previo para refinar.",
                instance="/pipeline/discovery/refine",
            )

        return DiscoveryRefinePhaseContext(
            current_document=current_document,
            user_instructions=user_instructions,
        )

    async def build_discovery_chat_context(
        self,
        project_id: ProjectId,
    ) -> DiscoveryChatContext:
        current_document = await self._document_repo.get_discovery(project_id)
        if current_document is None:
            raise PhaseTransitionError(
                detail="No existe un documento de descubrimiento para el chat.",
                instance="/pipeline/discovery/chat",
            )

        return DiscoveryChatContext(current_document=current_document)

    async def build_feature_chat_context(
        self,
        feature_id: FeatureId,
    ) -> FeatureChatContext:
        if self._feature_repo is None:
            raise ValueError("ContextBuilder no tiene FeatureRepository configurado.")

        feature = await self._feature_repo.by_id(feature_id)
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(feature_id),
                instance=f"/api/v1/features/{feature_id}/chat",
            )

        discovery_doc = await self._document_repo.get_discovery(feature.project_id)
        if discovery_doc is None:
            raise PhaseTransitionError(
                detail="No existe un documento de descubrimiento para el proyecto.",
                instance=f"/api/v1/features/{feature_id}/chat",
            )

        return FeatureChatContext(
            feature=feature,
            discovery_document=discovery_doc,
        )

    async def build_requirement_chat_context(
        self,
        feature_id: FeatureId,
        requirement_id: RequirementId,
    ) -> RequirementChatContext:
        if self._feature_repo is None:
            raise ValueError("ContextBuilder no tiene FeatureRepository configurado.")
        if self._requirement_repo is None:
            raise ValueError("ContextBuilder no tiene RequirementRepository configurado.")

        feature = await self._feature_repo.by_id(feature_id)
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(feature_id),
                instance=f"/pipeline/requirements/{requirement_id}/chat",
            )

        discovery_doc = await self._document_repo.get_discovery(feature.project_id)
        if discovery_doc is None:
            raise PhaseTransitionError(
                detail="No existe un documento de descubrimiento para el proyecto.",
                instance=f"/pipeline/requirements/{requirement_id}/chat",
            )

        markdown = await self._requirement_repo.by_feature_id(feature_id)
        if markdown is None:
            raise PhaseTransitionError(
                detail="No existen requisitos generados para esta caracteristica.",
                instance=f"/pipeline/requirements/{requirement_id}/chat",
            )

        requirement = _parse_requirement_from_markdown(markdown, feature_id, feature.number, requirement_id)
        if requirement is None:
            raise PhaseTransitionError(
                detail=f"Requisito {requirement_id} no encontrado en el documento de requisitos.",
                instance=f"/pipeline/requirements/{requirement_id}/chat",
            )

        return RequirementChatContext(
            requirement=requirement,
            feature=feature,
            discovery_document=discovery_doc,
        )


def _parse_requirement_from_markdown(
    markdown: str,
    feature_id: FeatureId,
    feature_number: int,
    requirement_id: RequirementId,
) -> EARSRequirement | None:
    display_prefix = f"REQ-{feature_number}."
    blocks = markdown.split("### ")
    for block in blocks[1:]:
        first_line = block.split("\n")[0] if block else ""
        prefix = "### " if not block.startswith("REQ-") else ""
        header_match = _req_header_re.match(f"{prefix}{first_line}")
        if not header_match:
            full_header = block.split("\n")[0] if block else ""
            header_match = _req_header_re.match(f"### {full_header}")
        if not header_match:
            continue

        display_id = header_match.group(1)
        if not display_id.startswith(display_prefix):
            continue

        req_num_str = display_id.split(".")[-1]
        try:
            requirement_number = int(req_num_str)
        except ValueError:
            continue

        title = header_match.group(2).strip()

        pattern_match = _req_pattern_re.search(block)
        pattern_str = pattern_match.group(1) if pattern_match else "Ubicuo"
        from kosmo.contracts.sdd.document import EARSPattern

        pattern_map: dict[str, EARSPattern] = {
            "Ubicuo": EARSPattern.ubiquitous,
            "Basado en eventos": EARSPattern.event_driven,
            "Determinado por estado": EARSPattern.state_driven,
            "Opcional": EARSPattern.optional,
            "Comportamiento no deseado": EARSPattern.unwanted,
            "Complejo": EARSPattern.complex,
        }
        pattern = pattern_map.get(pattern_str, EARSPattern.ubiquitous)

        lines = block.split("\n")
        statement_lines: list[str] = []
        criteria_section = False
        pattern_found = False
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("**") and ("Criterios" in stripped or "Escenario" in stripped):
                criteria_section = True
                break
            if stripped.startswith("**") and not pattern_found:
                pattern_found = True
                continue
            if stripped and not stripped.startswith("**"):
                statement_lines.append(stripped)
        statement = " ".join(statement_lines).strip()

        acceptance_criteria: list[AcceptanceCriterion] = []
        if criteria_section:
            ac_blocks = block.split("**Escenario:")
            for ac_block in ac_blocks[1:]:
                scenario_match = _ac_scenario_re.search("**Escenario:" + ac_block)
                given_match = _ac_given_re.search(ac_block)
                when_match = _ac_when_re.search(ac_block)
                then_match = _ac_then_re.search(ac_block)
                if scenario_match:
                    acceptance_criteria.append(
                        AcceptanceCriterion(
                            scenario=scenario_match.group(1).strip(),
                            given=given_match.group(1).strip() if given_match else "",
                            when=when_match.group(1).strip() if when_match else "",
                            then=then_match.group(1).strip() if then_match else "",
                        )
                    )

        origin = ""
        from datetime import UTC, datetime

        return EARSRequirement(
            id=requirement_id,
            feature_id=feature_id,
            feature_number=feature_number,
            requirement_number=requirement_number,
            title=title,
            pattern=pattern,
            statement=statement,
            origin=origin,
            acceptance_criteria=acceptance_criteria,
            created_at=datetime.now(UTC),
        )

    return None
