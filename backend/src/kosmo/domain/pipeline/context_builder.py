from __future__ import annotations

from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryPhaseContext,
    EARSPhaseContext,
    FeaturesPhaseContext,
    SuggestFeaturesContext,
)
from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState
from kosmo.contracts.sdd.document import FeatureStatus, RichTextDocument, SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotApprovedError, FeatureNotFoundError
from kosmo.contracts.sdd.repositories import DocumentRepository, ProjectRepository


class ContextBuilder:
    def __init__(
        self,
        document_repo: DocumentRepository,
        project_repo: ProjectRepository,
    ) -> None:
        self._document_repo = document_repo
        self._project_repo = project_repo

    async def build_context(
        self,
        state: KOSMOPipelineState,
        phase: SpecPhase,
    ) -> DiscoveryPhaseContext | FeaturesPhaseContext | EARSPhaseContext:
        builders = {
            SpecPhase.DESCUBRIMIENTO: self._build_discovery_context,
            SpecPhase.CARACTERISTICAS: self._build_features_context,
            SpecPhase.REQUISITOS: self._build_ears_context,
        }
        builder = builders.get(phase)
        if builder is None:
            raise PhaseTransitionError(
                detail=f"La fase {phase.value} no esta implementada en el pipeline actual",
                instance=f"/pipeline/phase/{phase.value}",
            )
        result = await builder(state)
        return result

    async def _build_discovery_context(
        self,
        state: KOSMOPipelineState,
    ) -> DiscoveryPhaseContext:
        project = await self._project_repo.by_id(state.project_id)
        if project is None:
            raise PhaseTransitionError(
                detail="No se encontro el proyecto para generar el discovery",
                instance="/pipeline/discovery",
            )
        return DiscoveryPhaseContext(
            project_name=project.name,
            project_description=project.description,
            user_preferences=state.user_preferences,
        )

    async def _build_features_context(
        self,
        state: KOSMOPipelineState,
    ) -> FeaturesPhaseContext:
        doc = await self._get_discovery_document(state)
        return FeaturesPhaseContext(
            discovery_document=doc,
            existing_feature_titles=[f.title for f in state.features],
            user_preferences=state.user_preferences,
        )

    async def _build_ears_context(
        self,
        state: KOSMOPipelineState,
    ) -> EARSPhaseContext:
        raise PhaseTransitionError(
            detail="EARS context debe construirse con feature_id especifico. Use build_ears_context_for_feature().",
            instance="/pipeline/requirements",
        )

    async def build_ears_context_for_feature(
        self,
        state: KOSMOPipelineState,
        feature_id: str,
    ) -> EARSPhaseContext:
        doc = await self._get_discovery_document(state)
        feature = next(
            (f for f in state.features if f.id == feature_id),
            None,
        )
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=feature_id,
                instance=f"/features/{feature_id}",
            )
        if feature.status != FeatureStatus.aprobada:
            raise FeatureNotApprovedError(
                feature_id=feature_id,
                instance=f"/features/{feature_id}/requirements",
            )
        feature_number = self._get_feature_number(state, feature_id)
        return EARSPhaseContext(
            discovery_document=doc,
            feature=feature,
            feature_number=feature_number,
            user_preferences=state.user_preferences,
        )

    async def build_suggest_features_context(
        self,
        state: KOSMOPipelineState,
    ) -> SuggestFeaturesContext:
        doc = await self._get_discovery_document(state)
        next_number = len(state.features) + 1
        return SuggestFeaturesContext(
            discovery_document=doc,
            existing_feature_titles=[f.title for f in state.features],
            next_feature_number=next_number,
            user_preferences=state.user_preferences,
        )

    async def _get_discovery_document(self, state: KOSMOPipelineState) -> RichTextDocument:
        doc = await self._document_repo.get_discovery(state.project_id)
        if doc is None:
            raise PhaseTransitionError(
                detail="No se encontro el documento de discovery para este proyecto",
                instance="/pipeline/discovery",
            )
        return doc

    def _get_feature_number(
        self,
        state: KOSMOPipelineState,
        feature_id: str,
    ) -> int:
        for idx, f in enumerate(state.features, start=1):
            if f.id == feature_id:
                return idx
        return 1
