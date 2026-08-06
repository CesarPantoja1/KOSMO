from __future__ import annotations

from ulid import ULID

from kosmo.contracts.consistency import (
    ArtifactAction,
    ConsistencyEvaluationOutput,
    ImpactItem,
)
from kosmo.contracts.sdd.document import SPEC_TO_API_PHASE, SpecPhase
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.requirements_markdown import parse_requirements_markdown

_SOURCE_LABEL: dict[SpecPhase, str] = {
    SpecPhase.DESCUBRIMIENTO: "Descubrimiento",
    SpecPhase.CARACTERISTICAS: "Características",
    SpecPhase.REQUISITOS: "Requisitos",
    SpecPhase.MODELO: "Modelo",
}


async def enrich_impact_items(
    result: ConsistencyEvaluationOutput,
    target_spec: SpecPhase,
    source_phase: SpecPhase,
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    diagram_repo: ActivityDiagramRepository,
) -> list[ImpactItem]:
    items: list[ImpactItem] = []

    action_by_id: dict[str, ArtifactAction] = {}
    for a in result.actions:
        action_by_id[a.artifact_id] = a

    source_label = _SOURCE_LABEL.get(source_phase, source_phase.value)

    if target_spec == SpecPhase.DESCUBRIMIENTO:
        for artifact_id in result.affected_artifact_ids:
            action = action_by_id.get(artifact_id)
            per_rationale = action.rationale if action else result.rationale
            per_action = action.action if action else "update"

            diff: dict[str, object] | None = None
            if action and action.suggested_before and action.suggested_after:
                diff = {
                    "field": action.suggested_field or "content",
                    "before": action.suggested_before,
                    "after": action.suggested_after,
                }

            items.append(
                ImpactItem(
                    id=f"imp_{ULID().hex}",
                    phase=SPEC_TO_API_PHASE[target_spec],
                    target_id=artifact_id,
                    artifact_type="DiscoveryDocument",
                    target_display_id=artifact_id,
                    target_title="Documento de Descubrimiento",
                    section=action.suggested_field if action else "content",
                    rationale=per_rationale or f"El cambio en {source_label} afecta el documento de Descubrimiento.",
                    diff=diff,
                    action=per_action,
                )
            )
        return items

    for fid_str in result.affected_artifact_ids:
        feature = await feature_repo.by_id(FeatureId(fid_str))
        if feature is None:
            continue

        action = action_by_id.get(fid_str)
        per_rationale = action.rationale if action else result.rationale
        per_action = action.action if action else "update"

        diff: dict[str, object] | None = None
        if action and action.suggested_before and action.suggested_after:
            diff = {
                "field": action.suggested_field or "description",
                "before": action.suggested_before,
                "after": action.suggested_after,
            }

        item_id = f"imp_{ULID().hex}"

        if target_spec == SpecPhase.CARACTERISTICAS:
            items.append(
                ImpactItem(
                    id=item_id,
                    phase=SPEC_TO_API_PHASE[target_spec],
                    target_id=fid_str,
                    artifact_type="Feature",
                    target_display_id=feature.display_id,
                    target_title=feature.title,
                    section=action.suggested_field if action else "title",
                    rationale=per_rationale
                    or (
                        "Esta característica ya no aplica al estado actual."
                        if per_action == "delete"
                        else f"El cambio en {source_label} afecta esta característica."
                    ),
                    diff=diff,
                    action=per_action,
                )
            )
        elif target_spec == SpecPhase.REQUISITOS:
            req_md = await requirement_repo.by_feature_id(feature.id)
            if req_md is None:
                continue

            current_reqs = parse_requirements_markdown(req_md, feature.id, feature.number)

            if action and action.suggested_before and action.suggested_after:
                before_reqs = parse_requirements_markdown(action.suggested_before, feature.id, feature.number)
                after_reqs = parse_requirements_markdown(action.suggested_after, feature.id, feature.number)
                before_by_id = {r.display_id: r for r in before_reqs}
                after_by_id = {r.display_id: r for r in after_reqs}
                all_ids = sorted(set(before_by_id.keys()) | set(after_by_id.keys()))
            else:
                before_by_id = {r.display_id: r for r in current_reqs}
                after_by_id = {}
                all_ids = sorted(before_by_id.keys())

            for req_display_id in all_ids:
                before_req = before_by_id.get(req_display_id)
                after_req = after_by_id.get(req_display_id)

                if before_req and after_req and before_req.statement != after_req.statement:
                    per_diff: dict[str, object] | None = {
                        "field": "statement",
                        "before": before_req.statement,
                        "after": after_req.statement,
                    }
                    req_action = "update"
                elif before_req and not after_req:
                    per_diff = None
                    req_action = "delete"
                elif not before_req and after_req:
                    per_diff = {
                        "field": "statement",
                        "before": "",
                        "after": after_req.statement,
                    }
                    req_action = "create"
                else:
                    per_diff = None
                    req_action = per_action

                target_req = before_req or after_req
                req_title = target_req.title if target_req else req_display_id
                items.append(
                    ImpactItem(
                        id=f"imp_{ULID().hex}",
                        phase=SPEC_TO_API_PHASE[target_spec],
                        target_id=fid_str,
                        artifact_type="EARSRequirement",
                        target_display_id=req_display_id,
                        target_title=req_title,
                        section="statement",
                        rationale=per_rationale
                        or (
                            "Se eliminará en cascada al eliminar la característica."
                            if req_action == "delete"
                            else f"El cambio en {source_label} afecta este requisito."
                        ),
                        diff=per_diff,
                        action=req_action,
                    )
                )
        elif target_spec == SpecPhase.MODELO:
            exists = await diagram_repo.exists(feature.id)
            if exists:
                items.append(
                    ImpactItem(
                        id=item_id,
                        phase=SPEC_TO_API_PHASE[target_spec],
                        target_id=fid_str,
                        artifact_type="ActivityDiagram",
                        target_display_id=feature.display_id,
                        target_title=f"Diagrama de {feature.title}",
                        section=action.suggested_field if action else "estructura UML",
                        rationale=per_rationale or "El cambio podría requerir actualizar el diagrama de actividad.",
                        diff=diff,
                        action=per_action,
                    )
                )

    return items


def impact_item_to_dict(item: ImpactItem) -> dict[str, object]:
    return {
        "id": item.id,
        "phase": item.phase,
        "targetId": item.target_id,
        "artifact_type": item.artifact_type,
        "targetDisplayId": item.target_display_id,
        "targetTitle": item.target_title,
        "section": item.section,
        "rationale": item.rationale,
        "diff": item.diff,
        "action": item.action,
    }
