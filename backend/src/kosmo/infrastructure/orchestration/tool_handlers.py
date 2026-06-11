from __future__ import annotations

import functools

from kosmo.contracts.orchestration.tools import ToolDefinition, ToolResult

from kosmo.contracts.sdd.feature import FeatureStatus


async def search_discovery_handler(
    params: dict[str, object],
    spec_repo: object | None = None,
) -> ToolResult:
    query = str(params.get("query", ""))
    project_id = str(params.get("project_id", ""))

    if not spec_repo or not project_id:
        return ToolResult(success=False, error="spec_repo or project_id not available")

    try:
        from kosmo.contracts.sdd.ids import ProjectId

        document_repo = getattr(spec_repo, "_document_repo", None)
        if document_repo is None:
            return ToolResult(success=True, data={"sections": {}, "found": False})

        markdown = await document_repo.get_discovery_md(ProjectId(project_id))
        if not markdown:
            return ToolResult(success=True, data={"sections": {}, "found": False})

        sections: dict[str, str] = {}
        if query:
            lines = markdown.split("\n")
            for line in lines:
                if query.lower() in line.lower():
                    sections["markdown"] = markdown[:2000]
                    break
        else:
            sections["markdown"] = markdown[:2000]

        return ToolResult(
            success=True,
            data={"sections": sections, "found": len(sections) > 0},
        )
    except Exception as exc:
        return ToolResult(success=False, error=str(exc))


async def search_features_handler(
    params: dict[str, object],
    feature_repo: object | None = None,
) -> ToolResult:
    query = str(params.get("query", ""))
    project_id = str(params.get("project_id", ""))

    if not feature_repo or not project_id:
        return ToolResult(success=False, error="feature_repo or project_id not available")

    try:
        features = await feature_repo.list_by_project(project_id)
        query_lower = query.lower()
        matches = []
        for f in features:
            if query_lower and (
                query_lower in f.title.lower() or query_lower in f.description.lower()
            ):
                matches.append(
                    {
                        "id": f.id,
                        "title": f.title,
                        "description": f.description[:500],
                        "status": f.status.value,
                    }
                )

        return ToolResult(
            success=True,
            data={"features": matches, "count": len(features), "matches": len(matches)},
        )
    except Exception as exc:
        return ToolResult(success=False, error=str(exc))


async def get_project_context_handler(
    params: dict[str, object],
    project_repo: object | None = None,
) -> ToolResult:
    project_id = str(params.get("project_id", ""))

    if not project_repo:
        return ToolResult(success=False, error="project_repo not available")

    try:
        project = await project_repo.get(project_id)
        if project is None:
            return ToolResult(success=False, error=f"Project {project_id} not found")

        return ToolResult(
            success=True,
            data={
                "id": project.id,
                "name": project.name,
                "description": project.description[:1000] if project.description else "",
                "phase": project.phase.value,
            },
        )
    except Exception as exc:
        return ToolResult(success=False, error=str(exc))


async def count_features_handler(
    params: dict[str, object],
    feature_repo: object | None = None,
) -> ToolResult:
    project_id = str(params.get("project_id", ""))

    if not feature_repo or not project_id:
        return ToolResult(success=False, error="feature_repo or project_id not available")

    try:
        features = await feature_repo.list_by_project(project_id)
        approved = [f for f in features if f.status.value == FeatureStatus.APROBADA.value]
        return ToolResult(
            success=True,
            data={
                "total": len(features),
                "approved": len(approved),
                "draft": len(features) - len(approved),
            },
        )
    except Exception as exc:
        return ToolResult(success=False, error=str(exc))


def build_sdd_tools(
    spec_repo: object | None = None,
    project_repo: object | None = None,
    feature_repo: object | None = None,
) -> list[tuple[ToolDefinition, object]]:
    tools: list[tuple[ToolDefinition, object]] = []

    search_discovery = ToolDefinition(
        name="search_discovery",
        description="Search sections of the project's discovery document by keyword or section name",
    )
    search_features = ToolDefinition(
        name="search_features",
        description="Search existing features by keyword to verify overlap or find related features",
    )
    get_project_context = ToolDefinition(
        name="get_project_context",
        description="Get project context: name, description, current phase",
    )
    count_features = ToolDefinition(
        name="count_features",
        description="Count total, approved, and draft features for the project",
    )

    tools.append(
        (
            search_discovery,
            functools.partial(search_discovery_handler, spec_repo=spec_repo),
        )
    )
    tools.append(
        (
            search_features,
            functools.partial(search_features_handler, feature_repo=feature_repo),
        )
    )
    tools.append(
        (
            get_project_context,
            functools.partial(get_project_context_handler, project_repo=project_repo),
        )
    )
    tools.append(
        (
            count_features,
            functools.partial(count_features_handler, feature_repo=feature_repo),
        )
    )

    return tools
