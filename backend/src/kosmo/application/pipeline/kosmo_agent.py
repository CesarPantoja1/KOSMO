from __future__ import annotations

import json
import time
from typing import Any

from kosmo.contracts.agent_memory import AgentMemoryPort
from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.orchestrator_ports import PhaseMode
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.agent_memory.session_factory import create_session
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.domain.pipeline.tool_registry import ToolRegistry


class KOSMOAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        max_iterations: int = 8,
        skill_registry: SkillRegistry | None = None,
        memory: AgentMemoryPort | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._registry = registry
        self._max_iterations = max_iterations
        self._skill_registry: SkillRegistry | None = skill_registry
        self._memory = memory

    async def execute_with_skill(
        self,
        skill_name: str,
        context: Any,
        *,
        project_id: ProjectId | None = None,
        user_instructions: str | None = None,
    ) -> Any:
        if self._skill_registry is None:
            raise ValueError("SkillRegistry no configurado")
        mode = self._skill_registry.resolve(skill_name)
        return await self._execute_loop(
            mode,
            context,
            skill_name=skill_name,
            project_id=project_id,
            user_instructions=user_instructions,
        )

    async def _execute_loop(
        self,
        mode: PhaseMode,
        context: Any,
        *,
        skill_name: str | None = None,
        project_id: ProjectId | None = None,
        user_instructions: str | None = None,
    ) -> Any:
        start_time = time.monotonic()
        system_prompt = mode.system_prompt

        if self._memory is not None and project_id is not None:
            project_context = await self._memory.get_project_context(project_id)
            if project_context.total_sessions > 0:
                system_prompt = self._inject_context(system_prompt, project_context)

        user_prompt = mode.build_user_prompt(context)
        last_output: Any = None
        last_validation = ValidationResult(is_valid=False, errors=["No se genero contenido"])
        llm_calls = 0

        for _iteration in range(1, self._max_iterations + 1):
            try:
                last_output = await self._llm_client.complete_typed(
                    prompt=PromptTemplate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    ),
                    output_type=mode.output_type,
                    temperature=mode.temperature,
                    max_tokens=mode.max_tokens,
                )
            except Exception:
                break

            llm_calls += 1
            last_validation = mode.validate_output(last_output)

            if last_validation.is_valid:
                total_ms = int((time.monotonic() - start_time) * 1000)
                metadata = GenerationMetadata(
                    llm_calls=llm_calls,
                    retry_count=llm_calls - 1,
                    generation_time_ms=total_ms,
                )

                if self._memory is not None and project_id is not None:
                    await self._save_completed_session(
                        project_id=project_id,
                        phase=mode.phase_name,
                        session_type="refinement" if user_instructions else "generation",
                        skill_name=skill_name,
                        current_iteration=llm_calls,
                        output=last_output,
                        validation=last_validation,
                        user_instructions=user_instructions,
                    )

                return mode.build_output(last_output, last_validation, metadata)

            user_prompt = (
                mode.build_user_prompt(context) + "\n\n" + mode.build_validation_feedback(last_validation.errors)
            )

        total_ms = int((time.monotonic() - start_time) * 1000)
        metadata = GenerationMetadata(
            llm_calls=llm_calls,
            retry_count=llm_calls - 1 if llm_calls > 0 else 0,
            generation_time_ms=total_ms,
        )
        return mode.build_output(last_output, last_validation, metadata)

    async def _save_completed_session(
        self,
        *,
        project_id: ProjectId,
        phase: SpecPhase,
        session_type: str,
        skill_name: str | None,
        current_iteration: int,
        output: Any,
        validation: ValidationResult,
        user_instructions: str | None,
    ) -> None:
        if self._memory is None:
            return

        output_json = json.dumps(output, default=str) if output else None

        session = create_session(
            project_id=project_id,
            session_type=session_type,
            phase=phase,
            skill_name=skill_name,
            max_iterations=self._max_iterations,
            conversation=[],
            reasoning_log=[],
            tool_results=[],
            current_iteration=current_iteration,
            is_completed=True,
            output_json=output_json,
            validation_is_valid=validation.is_valid,
            validation_errors=len(validation.errors),
            total_llm_calls=current_iteration,
            user_instructions=user_instructions,
        )

        await self._memory.save_session(session)

    def _inject_context(
        self,
        system_prompt: str,
        project_context: Any,
    ) -> str:
        from kosmo.contracts.agent_memory import ProjectMemoryContext

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

        return "\n\n".join(parts)

    @property
    def memory(self) -> AgentMemoryPort | None:
        return self._memory
