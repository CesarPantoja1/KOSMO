from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import TYPE_CHECKING, Any

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
from kosmo.domain.pipeline.guard_registry import GuardRegistry
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.domain.sdd.output_guardrails import sanitize_user_instructions

if TYPE_CHECKING:
    from kosmo.domain.pipeline.knowledge_tool_registry import KnowledgeToolRegistry


class KOSMOAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        guard_registry: GuardRegistry,
        max_iterations: int = 8,
        skill_registry: SkillRegistry | None = None,
        memory: AgentMemoryPort | None = None,
        embedding_generator: Any = None,
        knowledge_tools: KnowledgeToolRegistry | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._guard_registry = guard_registry
        self._max_iterations = max_iterations
        self._skill_registry: SkillRegistry | None = skill_registry
        self._memory = memory
        self._embedder: Any = embedding_generator  # EmbeddingGenerator
        self._knowledge_tools: KnowledgeToolRegistry | None = knowledge_tools

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

        sanitized_instructions = sanitize_user_instructions(user_instructions) if user_instructions else None

        mode = self._skill_registry.resolve(skill_name)
        return await self._execute_loop(
            mode,
            context,
            skill_name=skill_name,
            project_id=project_id,
            user_instructions=sanitized_instructions,
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

        base_user_prompt = mode.build_user_prompt(context)

        if self._embedder is not None and self._memory is not None and project_id is not None:
            query_embedding = await self._embedder.embed(base_user_prompt)
            if query_embedding is not None:
                similar = await self._memory.get_similar_sessions(
                    query_embedding,
                    limit=3,
                    exclude_project_id=project_id,
                )
                if similar:
                    system_prompt = self._inject_cross_project_context(system_prompt, similar)

        knowledge_context = ""
        if self._knowledge_tools is not None:
            tools_desc = self._knowledge_tools.describe_for_llm()
            if tools_desc:
                tool_system_prompt = system_prompt + "\n\n" + tools_desc
                knowledge_context = await self._resolve_knowledge_tools(
                    tool_system_prompt, base_user_prompt, project_id
                )

        user_prompt = base_user_prompt
        if knowledge_context:
            user_prompt += "\n\n## Informacion adicional recuperada\n\n" + knowledge_context

        last_output: Any = None
        last_validation = ValidationResult(is_valid=False, errors=["No se genero contenido"])
        llm_calls = 0
        conversation: list[str] = []

        for iteration in range(1, self._max_iterations + 1):
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
            last_validation = mode.validate_output(last_output, context=context)

            conversation.append(
                json.dumps(
                    {
                        "iteration": iteration,
                        "user_prompt": user_prompt[:500],
                        "output_snippet": str(last_output)[:500],
                        "is_valid": last_validation.is_valid,
                    },
                    ensure_ascii=False,
                )
            )

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
                        conversation=conversation,
                    )

                return mode.build_output(last_output, last_validation, metadata, context=context)

            delay_s = min(1.0 * (2 ** (iteration - 1)), 30.0)
            await asyncio.sleep(delay_s)

            user_prompt = base_user_prompt + "\n\n" + mode.build_validation_feedback(last_validation.errors)

        total_ms = int((time.monotonic() - start_time) * 1000)
        metadata = GenerationMetadata(
            llm_calls=llm_calls,
            retry_count=llm_calls - 1 if llm_calls > 0 else 0,
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
                conversation=conversation,
                is_completed=False,
            )

        return mode.build_output(last_output, last_validation, metadata, context=context)

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
        conversation: list[str] | None = None,
        is_completed: bool = True,
    ) -> None:
        if self._memory is None:
            return

        output_json = json.dumps(output, default=str) if output else None

        embedding: list[float] | None = None
        if self._embedder is not None and output is not None:
            text = self._embedder.text_for_embedding(output, validation.errors)
            embedding = await self._embedder.embed(text)

        reflection = await self._generate_reflection(
            phase=phase,
            session_type=session_type,
            is_completed=is_completed,
            current_iteration=current_iteration,
            validation=validation,
        )

        session = create_session(
            project_id=project_id,
            session_type=session_type,
            phase=phase,
            skill_name=skill_name,
            max_iterations=self._max_iterations,
            conversation=conversation or [],
            reasoning_log=[],
            tool_results=[],
            current_iteration=current_iteration,
            is_completed=is_completed,
            output_json=output_json,
            validation_is_valid=validation.is_valid,
            validation_errors=len(validation.errors),
            total_llm_calls=current_iteration,
            user_instructions=user_instructions,
            embedding=embedding,
            reflection=reflection,
        )

        await self._memory.save_session(session)

    async def _resolve_knowledge_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        project_id: ProjectId | None,
    ) -> str:
        if self._knowledge_tools is None:
            return ""

        tool_prompt = PromptTemplate(
            system_prompt=(
                system_prompt + "\n\nIMPORTANTE: Antes de generar, puedes consultar herramientas de conocimiento "
                "para obtener informacion adicional. Responde SOLO con uno de estos formatos:\n\n"
                '- [TOOL: nombre] {"arg": "valor"}  (para consultar una herramienta)\n'
                "- [CONTINUE]  (si ya tienes suficiente contexto)\n\n"
                "El resultado de la herramienta se te proporcionara y podras continuar."
            ),
            user_prompt=user_prompt,
        )

        collected: list[str] = []
        for _ in range(3):
            try:
                response = await self._llm_client.complete(
                    prompt=tool_prompt,
                    temperature=0.1,
                    max_tokens=200,
                )
            except Exception:
                break

            text = response.text.strip()
            if "[CONTINUE]" in text:
                break

            tool_name, tool_args = _parse_tool_call(text)
            if tool_name is None:
                break

            if project_id is not None:
                tool_args.setdefault("project_id", str(project_id))

            result = await self._knowledge_tools.execute(tool_name, tool_args)
            if result is None:
                collected.append(f"[TOOL: {tool_name}] Herramienta no encontrada")
                continue

            collected.append(f"[TOOL: {tool_name}]\n{result}")
            tool_prompt = PromptTemplate(
                system_prompt=tool_prompt.system_prompt,
                user_prompt=user_prompt + "\n\n" + collected[-1] + "\n\nResponde [CONTINUE] o [TOOL: ...]",
            )

        return "\n\n".join(collected)

    async def _generate_reflection(
        self,
        *,
        phase: SpecPhase,
        session_type: str,
        is_completed: bool,
        current_iteration: int,
        validation: ValidationResult,
    ) -> str | None:
        if is_completed and current_iteration == 1 and validation.is_valid:
            return None

        status = "completada exitosamente" if is_completed else "fallida"
        errors_text = "; ".join(validation.errors[:5]) if validation.errors else "ninguno"

        prompt = PromptTemplate(
            system_prompt=(
                "Eres un analista de calidad que revisa sesiones de un agente de IA. "
                "Genera UNA sola leccion aprendida en espanol, en maximo 2 oraciones, "
                "que ayude al agente a mejorar en futuras sesiones. "
                "Se especifico: menciona que patron evitar o que enfoque usar. "
                "Responde solo con el texto de la leccion, sin prefijos ni markdown."
            ),
            user_prompt=(
                f"Fase: {phase.value}\n"
                f"Tipo: {session_type}\n"
                f"Estado: {status}\n"
                f"Iteraciones usadas: {current_iteration} de {self._max_iterations}\n"
                f"Errores de validacion: {errors_text}\n\n"
                "Genera una leccion aprendida:"
            ),
        )

        try:
            result = await self._llm_client.complete(
                prompt=prompt,
                temperature=0.3,
                max_tokens=150,
            )
            text = result.text.strip()
            if text and len(text) > 10:
                return text
        except Exception:
            pass

        return None

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
        from kosmo.contracts.agent_memory import AgentSessionSummary

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

    @property
    def memory(self) -> AgentMemoryPort | None:
        return self._memory


def _parse_tool_call(text: str) -> tuple[str | None, dict[str, Any]]:
    marker = "[TOOL:"
    if marker not in text:
        return None, {}

    idx = text.index(marker) + len(marker)
    end_name = text.index("]", idx) if "]" in text[idx:] else len(text)
    tool_name = text[idx:end_name].strip()

    args: dict[str, Any] = {}
    brace_start = text.find("{", end_name)
    if brace_start != -1:
        brace_end = text.find("}", brace_start)
        if brace_end != -1:
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                args = json.loads(text[brace_start : brace_end + 1])

    return tool_name, args
