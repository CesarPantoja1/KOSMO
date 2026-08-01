from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryChatContext,
    DiscoveryRefinePhaseContext,
    FeatureChatContext,
    RequirementChatContext,
)
from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
from kosmo.contracts.sdd.document import AcceptanceCriterion, EARSPattern
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, RequirementId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.requirements_markdown import parse_requirement_from_markdown


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

        requirement_model = await _find_requirement_item(self._requirement_repo, feature_id, requirement_id)
        if requirement_model is None:
            markdown = await self._requirement_repo.by_feature_id(feature_id)
            if markdown is None:
                raise PhaseTransitionError(
                    detail="No existen requisitos generados para esta caracteristica.",
                    instance=f"/pipeline/requirements/{requirement_id}/chat",
                )
            requirement = parse_requirement_from_markdown(markdown, feature_id, feature.number, requirement_id)
        else:
            requirement = _model_to_ears_requirement(requirement_model, feature_id, feature.number)

        if requirement is None:
            raise PhaseTransitionError(
                detail=f"Requisito {requirement_id} no encontrado.",
                instance=f"/pipeline/requirements/{requirement_id}/chat",
            )

        return RequirementChatContext(
            requirement=requirement,
            feature=feature,
            discovery_document=discovery_doc,
        )


async def _find_requirement_item(
    repo: RequirementRepository, feature_id: FeatureId, req_id: RequirementId
) -> object | None:
    try:
        items = await repo.list_items(feature_id)  # type: ignore[reportAttributeAccessIssue]
    except Exception:
        return None
    for item in items:  # type: ignore[reportUnknownVariableType]
        if getattr(item, "id", "") == str(req_id):
            return item
    return None


def _model_to_ears_requirement(model: object, feature_id: FeatureId, feature_number: int) -> EARSRequirement:
    ac_raw: list[dict[str, Any]] = _safe_list(getattr(model, "acceptance_criteria", None))
    return EARSRequirement(
        id=RequirementId(str(getattr(model, "id", ""))),
        feature_id=feature_id,
        feature_number=feature_number,
        requirement_number=int(getattr(model, "requirement_number", 0)),
        title=str(getattr(model, "title", "")),
        pattern=EARSPattern(str(getattr(model, "pattern", "ubiquitous"))),
        statement=str(getattr(model, "statement", "")),
        origin=str(getattr(model, "origin", "")),
        acceptance_criteria=[
            AcceptanceCriterion(
                scenario=str(ac.get("scenario", "")),
                given=str(ac.get("given", "")),
                when=str(ac.get("when", "")),
                then=str(ac.get("then", "")),
            )
            for ac in ac_raw
        ],
        created_at=getattr(model, "created_at", datetime.now(UTC)),
    )


def _safe_list(value: object) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[dict[str, Any]] = []
        for item in value:  # type: ignore[reportUnknownVariableType]
            if isinstance(item, dict):
                result.append({str(k): v for k, v in item.items()})  # type: ignore[reportUnknownVariableType]
        return result
    return []
    if isinstance(value, list):
        return [dict(item) if isinstance(item, dict) else {} for item in value]  # type: ignore[reportUnknownVariableType]
    return []

