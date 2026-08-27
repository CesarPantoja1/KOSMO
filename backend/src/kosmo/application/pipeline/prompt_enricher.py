from __future__ import annotations

import asyncio
from typing import Any

from kosmo.contracts.memory.agent_memory import (
    AgentMemoryPort,
    AgentSessionSummary,
    KnowledgePatternStore,
    ProjectMemoryContext,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId


class PromptEnricher:
    """Enriquece el system prompt con memoria del proyecto, sesiones similares y patrones."""

    def __init__(
        self,
        *,
        memory: AgentMemoryPort | None = None,
        pattern_store: KnowledgePatternStore | None = None,
        embedder: Any = None,
    ) -> None:
        self._memory = memory
        self._pattern_store = pattern_store
        self._embedder: Any = embedder

    async def enrich(
        self,
        system_prompt: str,
        base_user_prompt: str,
        project_id: ProjectId | None,
        *,
        phase: SpecPhase | None = None,
    ) -> str:
        memory_task: asyncio.Task[object] | None = None
        patterns_task: asyncio.Task[object] | None = None
        embed_task: asyncio.Task[object] | None = None

        if self._memory is not None and project_id is not None:
            memory_task = asyncio.create_task(self._memory.get_project_context(project_id))

        if self._pattern_store is not None and phase is not None:
            patterns_task = asyncio.create_task(self._pattern_store.list_patterns(phase=phase, limit=5))

        if self._embedder is not None and self._memory is not None and project_id is not None:

            async def _embed_and_search() -> Any:
                query_embedding = await self._embedder.embed(base_user_prompt)  # type: ignore[reportOptionalMemberAccess]
                if query_embedding is None:
                    return None
                similar = await self._memory.get_similar_sessions(  # type: ignore[reportOptionalMemberAccess]
                    query_embedding,
                    limit=3,
                    exclude_project_id=project_id,
                    model=self._embedder.model_name if self._embedder else None,  # type: ignore[reportOptionalMemberAccess]
                )
                return similar if similar else None

            embed_task = asyncio.create_task(_embed_and_search())

        if memory_task is not None:
            project_context = await memory_task  # type: ignore[reportUnknownVariableType]
            if project_context.total_sessions > 0:
                system_prompt = self._inject_context(system_prompt, project_context)

        if embed_task is not None:
            similar = await embed_task  # type: ignore[reportUnknownVariableType]
            if similar:
                system_prompt = self._inject_cross_project_context(system_prompt, similar)  # type: ignore[reportArgumentType]

        if patterns_task is not None:
            patterns = await patterns_task
            if patterns:
                system_prompt = self._inject_patterns(system_prompt, patterns)

        return system_prompt

    def _inject_context(
        self,
        system_prompt: str,
        project_context: Any,
    ) -> str:
        if not isinstance(project_context, ProjectMemoryContext):
            return system_prompt

        parts: list[str] = [system_prompt]

        if project_context.total_sessions > 0:
            parts.append(
                "## Contexto acumulado del proyecto\n\n"
                f"Este proyecto tiene {project_context.total_sessions} sesiones previas "
                "del agente.\n"
            )

            for _key, session in project_context.latest_sessions.items():
                parts.append(
                    f"- Fase {session.phase.value} ({session.session_type}): "
                    f"{'completada' if session.is_completed else 'incompleta'}, "
                    f"{session.total_llm_calls} llamadas LLM"
                )
                if session.user_instructions:
                    parts.append(f"  Instruccion del usuario: {session.user_instructions}")

            parts.append(
                "Utiliza este contexto para mantener consistencia con el trabajo previo: "
                "mismo nivel de detalle, mismo estilo de redaccion, mismas convenciones."
            )

        if project_context.common_validation_errors:
            parts.append(
                "Errores de validacion frecuentes en sesiones previas:\n"
                + "\n".join(f"- {e}" for e in project_context.common_validation_errors)
            )

        if project_context.recent_reflections:
            parts.append(
                "## Reflexiones de sesiones previas\n\n"
                + "\n".join(f"- {r}" for r in project_context.recent_reflections)
                + "\n\nAplica estas lecciones aprendidas para evitar repetir errores."
            )

        return "\n\n".join(parts)

    def _inject_cross_project_context(
        self,
        system_prompt: str,
        similar: list[Any],
    ) -> str:
        lines: list[str] = [
            system_prompt,
            "## Sesiones similares en otros proyectos\n\n"
            "Los siguientes proyectos tienen sesiones con contenido similar "
            "al que vas a generar. Usa esta informacion para mantener "
            "consistencia en el estilo y nivel de detalle:\n",
        ]
        for s in similar:
            if not isinstance(s, AgentSessionSummary):
                continue
            lines.append(
                f"- Proyecto {s.project_id}, fase {s.phase.value} ({s.session_type}): "
                f"{'completada' if s.is_completed else 'incompleta'}, "
                f"{s.total_llm_calls} llamadas LLM"
            )
            if s.user_instructions:
                lines.append(f"  Instrucciones: {s.user_instructions}")
        return "\n".join(lines)

    def _inject_patterns(
        self,
        system_prompt: str,
        patterns: list[Any],
    ) -> str:
        lines: list[str] = [
            system_prompt,
            "## Patrones aprendidos entre proyectos\n\n"
            "Los siguientes patrones se han identificado al analizar sesiones "
            "de multiples proyectos. Usa esta informacion para mejorar la calidad:\n",
        ]
        for p in patterns:
            lines.append(f"- {p.pattern_text} (respaldado por {p.support_count} proyectos)")
        return "\n".join(lines)
