from __future__ import annotations

from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryPhaseContext,
    EARSPhaseContext,
    FeaturesPhaseContext,
    SuggestFeaturesContext,
)
from kosmo.contracts.pipeline.phase_errors import PhaseTransitionError
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
)


class ContextBuilder:
    def __init__(
        self,
        document_repo: DocumentRepository,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
    ) -> None:
        self._document_repo = document_repo
        self._project_repo = project_repo
        self._feature_repo = feature_repo

    async def build_context(
        self,
        project_id: ProjectId,
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
        result = await builder(project_id)
        return result

    async def _build_discovery_context(
        self,
        project_id: ProjectId,
    ) -> DiscoveryPhaseContext:
        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise PhaseTransitionError(
                detail="No se encontro el proyecto para generar el discovery",
                instance="/pipeline/discovery",
            )
        return DiscoveryPhaseContext(
            project_name=project.name,
            project_description=project.description,
        )

    async def _build_features_context(
        self,
        project_id: ProjectId,
    ) -> FeaturesPhaseContext:
        doc = await self._get_discovery_document(project_id)
        features = await self._feature_repo.list_by_project(project_id)
        return FeaturesPhaseContext(
            discovery_document=doc,
            existing_feature_titles=[f.title for f in features],
        )

    async def _build_ears_context(
        self,
        project_id: ProjectId,  # noqa: ARG002
    ) -> EARSPhaseContext:
        raise PhaseTransitionError(
            detail="EARS context debe construirse con feature_id especifico."
            " Use build_ears_context_for_feature().",
            instance="/pipeline/requirements",
        )

    async def build_ears_context_for_feature(
        self,
        project_id: ProjectId,
        feature_id: FeatureId,
    ) -> EARSPhaseContext:
        doc = await self._get_discovery_document(project_id)
        feature = await self._feature_repo.by_id(feature_id)
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(feature_id),
                instance=f"/features/{feature_id}",
            )
        features = await self._feature_repo.list_by_project(project_id)
        feature_number = next(
            (i + 1 for i, f in enumerate(features) if f.id == feature_id),
            1,
        )
        return EARSPhaseContext(
            discovery_document=doc,
            feature=feature,
            feature_number=feature_number,
        )

    async def build_suggest_features_context(
        self,
        project_id: ProjectId,
    ) -> SuggestFeaturesContext:
        doc = await self._get_discovery_document(project_id)
        features = await self._feature_repo.list_by_project(project_id)
        next_number = len(features) + 1
        return SuggestFeaturesContext(
            discovery_document=doc,
            existing_feature_titles=[f.title for f in features],
            next_feature_number=next_number,
        )

    async def _get_discovery_document(self, project_id: ProjectId) -> RichTextDocument:
        doc = await self._document_repo.get_discovery(project_id)
        if doc is None:
            raise PhaseTransitionError(
                detail="No se encontro el documento de discovery para este proyecto",
                instance="/pipeline/discovery",
            )
        return doc
