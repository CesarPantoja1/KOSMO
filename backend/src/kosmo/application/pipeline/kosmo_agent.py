from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import time
from typing import TYPE_CHECKING, Any

import structlog

from kosmo.contracts.agent_memory import AgentMemoryPort, KnowledgePatternStore
from kosmo.contracts.chat import ChatRole, DiffCambio, MensajeChat, RespuestaChatLLM, SugerenciaCambio
from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.orchestrator_ports import PhaseMode
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import AgentMemoryId, ChatMessageId, ProjectId
from kosmo.domain.agent_memory.session_factory import create_session
from kosmo.domain.pipeline.guard_registry import GuardRegistry
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.domain.sdd.output_guardrails import sanitize_user_instructions

if TYPE_CHECKING:
    from kosmo.domain.pipeline.knowledge_tool_registry import KnowledgeToolRegistry

_CONSOLIDATION_THRESHOLD = 5

_log = structlog.get_logger(__name__)


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
        pattern_store: KnowledgePatternStore | None = None,
        consolidation_threshold: int = _CONSOLIDATION_THRESHOLD,
    ) -> None:
        self._llm_client = llm_client
        self._guard_registry = guard_registry
        self._max_iterations = max_iterations
        self._skill_registry: SkillRegistry | None = skill_registry
        self._memory = memory
        self._embedder: Any = embedding_generator  # EmbeddingGenerator
        self._knowledge_tools: KnowledgeToolRegistry | None = knowledge_tools
        self._pattern_store = pattern_store
        self._consolidation_threshold = consolidation_threshold

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

        context = _sanitize_context(context)

        mode = self._skill_registry.resolve(skill_name)
        return await self._execute_loop(
            mode,
            context,
            skill_name=skill_name,
            project_id=project_id,
            user_instructions=sanitized_instructions,
        )

    async def execute_conversation(
        self,
        skill_name: str,
        messages: list[MensajeChat],
        context: Any,
        *,
        project_id: ProjectId | None = None,
    ) -> MensajeChat:
        """Ejecuta una conversación con el LLM usando un skill de chat.

        El flujo incluye pre-consulta de knowledge tools, validación del output
        con un reintento, y persistencia de la sesión en memoria del agente.
        Las excepciones del LLM propagan hacia arriba para que el caso de uso
        las maneje con reintentos (tenacity) o las convierta en ErrorChat.
        """
        if self._skill_registry is None:
            raise ValueError("SkillRegistry no configurado")

        sanitized_ctx = _sanitize_context(context)
        mode = self._skill_registry.resolve(skill_name)

        system_prompt = mode.system_prompt
        base_user_prompt = mode.build_user_prompt(sanitized_ctx)

        knowledge_context = ""
        if self._knowledge_tools is not None and project_id is not None:
            tools_desc = self._knowledge_tools.describe_for_llm()
            if tools_desc:
                tool_system = system_prompt + "\n\n" + tools_desc
                try:
                    knowledge_context, _ = await self._resolve_knowledge_tools(
                        tool_system, base_user_prompt, project_id
                    )
                except Exception:
                    _log.warning("chat.tools_preflight_failed", exc_info=True)

        history_block = _format_chat_history(messages)
        user_prompt = f"{base_user_prompt}\n\n{history_block}\n\nResponde al ultimo mensaje del usuario."
        if knowledge_context:
            user_prompt += "\n\n## Informacion adicional recuperada\n\n" + knowledge_context

        prompt = PromptTemplate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        output: Any = None
        for attempt in range(2):
            try:
                output = await self._llm_client.complete_typed(
                    prompt=prompt,
                    output_type=mode.output_type,
                    temperature=mode.temperature,
                    max_tokens=mode.max_tokens,
                )
            except Exception:
                _log.warning("chat.llm_call_failed", attempt=attempt, exc_info=True)
                if attempt == 0:
                    continue
                break

            validation = mode.validate_output(output)
            if validation.is_valid:
                break

            if attempt == 0 and validation.errors:
                feedback = mode.build_validation_feedback(validation.errors)
                user_prompt += "\n\n" + feedback

        if output is None:
            output = RespuestaChatLLM(content="No se pudo generar una respuesta.", change_suggestion=None)
        elif not isinstance(output, RespuestaChatLLM):
            try:
                raw = await self._llm_client.complete(
                    prompt=prompt,
                    temperature=mode.temperature,
                    max_tokens=mode.max_tokens,
                )
                output = RespuestaChatLLM(content=raw.text.strip(), change_suggestion=None)
            except Exception:
                output = RespuestaChatLLM(content="No se pudo generar una respuesta.", change_suggestion=None)

        if self._memory is not None and project_id is not None:
            await self._save_chat_session(
                project_id=project_id,
                phase=mode.phase_name,
                skill_name=skill_name,
                messages=messages,
                output=output,
            )

        return _to_assistant_message(output)

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
                    model=self._embedder.model_name if self._embedder else None,
                )
                if similar:
                    system_prompt = self._inject_cross_project_context(system_prompt, similar)

        if self._pattern_store is not None:
            patterns = await self._pattern_store.list_patterns(phase=mode.phase_name, limit=5)
            if patterns:
                system_prompt = self._inject_patterns(system_prompt, patterns)

        knowledge_context = ""
        tool_invocations: list[dict[str, Any]] = []
        reason_entries: list[str] = []
        if self._knowledge_tools is not None:
            tools_desc = self._knowledge_tools.describe_for_llm()
            if tools_desc:
                tool_system_prompt = system_prompt + "\n\n" + tools_desc
                knowledge_context, tool_invocations = await self._resolve_knowledge_tools(
                    tool_system_prompt, base_user_prompt, project_id
                )
                if knowledge_context:
                    reason_entries.append(
                        "pre_consulta_tools: herramientas consultadas: "
                        + ", ".join(t["tool"] for t in tool_invocations if t.get("found"))
                        or "ninguna encontrada"
                    )
                else:
                    reason_entries.append("pre_consulta_tools: sin consulta de herramientas")
            else:
                reason_entries.append("pre_consulta_tools: sin herramientas registradas")
        else:
            reason_entries.append("pre_consulta_tools: no disponible")

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
                _log.warning("agent.llm_call_failed", skill_name=skill_name, iteration=iteration, exc_info=True)
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
                        reasoning_log=reason_entries,
                        tool_results=tool_invocations,
                    )

                return mode.build_output(last_output, last_validation, metadata, context=context)

            delay_s = min(1.0 * (2 ** (iteration - 1)), 30.0)
            await asyncio.sleep(delay_s)

            retry_context = ""
            if self._knowledge_tools is not None and last_validation.errors and iteration < self._max_iterations:
                error_list = "; ".join(last_validation.errors[:5])
                retry_system_prompt = (
                    system_prompt + "\n\nLa validacion del contenido generado fallo "
                    "con los siguientes errores. Puedes consultar herramientas "
                    "para corregir antes de reintentar."
                )
                retry_user_prompt = f"Errores de validacion: {error_list}"
                try:
                    retry_context, retry_records = await self._resolve_knowledge_tools(
                        retry_system_prompt, retry_user_prompt, project_id
                    )
                    if retry_records:
                        tool_invocations.extend(retry_records)
                        reason_entries.append(
                            f"retry_tools: iteracion {iteration}"
                            + " herramientas: "
                            + ", ".join(r["tool"] for r in retry_records if r.get("found"))
                        )
                except Exception:
                    _log.warning("agent.retry_tools_failed", iteration=iteration, exc_info=True)
                    pass

            feedback = mode.build_validation_feedback(last_validation.errors)
            user_prompt = base_user_prompt
            if retry_context:
                user_prompt += "\n\n## Informacion adicional del retry\n\n" + retry_context
            user_prompt += "\n\n" + feedback

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
                reasoning_log=reason_entries,
                tool_results=tool_invocations,
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
        reasoning_log: list[str] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        is_completed: bool = True,
    ) -> None:
        if self._memory is None:
            return

        output_json = json.dumps(output, default=str) if output else None

        embedding: list[float] | None = None
        if self._embedder is not None and output is not None:
            text = self._embedder.text_for_embedding(output, validation.errors)
            embedding = await self._embedder.embed(text)

        session = create_session(
            project_id=project_id,
            session_type=session_type,
            phase=phase,
            skill_name=skill_name,
            max_iterations=self._max_iterations,
            conversation=conversation or [],
            reasoning_log=reasoning_log or [],
            tool_results=tool_results or [],
            current_iteration=current_iteration,
            is_completed=is_completed,
            output_json=output_json,
            validation_is_valid=validation.is_valid,
            validation_errors=len(validation.errors),
            validation_error_messages=validation.errors[:10],
            total_llm_calls=current_iteration,
            user_instructions=user_instructions,
            embedding=embedding,
            embedding_model=self._embedder.model_name if self._embedder else None,
            reflection=None,
        )

        await self._memory.save_session(session)

        asyncio.create_task(
            self._reflect_and_consolidate(
                session_id=session.session_id,
                phase=phase,
                session_type=session_type,
                is_completed=is_completed,
                current_iteration=current_iteration,
                validation=validation,
            )
        )

    async def _save_chat_session(
        self,
        *,
        project_id: ProjectId,
        phase: SpecPhase,
        skill_name: str,
        messages: list[MensajeChat],
        output: Any,
    ) -> None:
        if self._memory is None:
            return

        output_json = json.dumps(output, default=str) if output else None
        conversation = [json.dumps({"role": m.role.value, "content": m.content[:200]}) for m in messages[-10:]]

        session = create_session(
            project_id=project_id,
            session_type="chat",
            phase=phase,
            skill_name=skill_name,
            conversation=conversation,
            output_json=output_json,
            current_iteration=1,
            max_iterations=1,
            is_completed=True,
            validation_is_valid=True,
            embedding=None,
            embedding_model=None,
        )

        await self._memory.save_session(session)

    async def _reflect_and_consolidate(
        self,
        *,
        session_id: AgentMemoryId,
        phase: SpecPhase,
        session_type: str,
        is_completed: bool,
        current_iteration: int,
        validation: ValidationResult,
    ) -> None:
        if self._memory is None:
            return

        reflection = await self._generate_reflection(
            phase=phase,
            session_type=session_type,
            is_completed=is_completed,
            current_iteration=current_iteration,
            validation=validation,
        )

        if reflection:
            await self._memory.update_reflection(session_id, reflection)

        if is_completed and self._pattern_store is not None:
            counts = await self._memory.count_completed_by_phase()
            for _phase, count in counts.items():
                if count >= self._consolidation_threshold and count % self._consolidation_threshold == 0:
                    from kosmo.application.knowledge import ConsolidateInput, ConsolidateKnowledgePatterns

                    uc = ConsolidateKnowledgePatterns(
                        memory=self._memory,
                        pattern_store=self._pattern_store,
                        llm_client=self._llm_client,
                    )
                    await uc.execute(ConsolidateInput(sessions_limit=min(count * 2, 100)))

    async def _resolve_knowledge_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        project_id: ProjectId | None,
    ) -> tuple[str, list[dict[str, Any]]]:
        if self._knowledge_tools is None:
            return ("", [])

        if getattr(self._llm_client, "supports_native_tools", False):
            try:
                text, records = await self._llm_client.complete_with_tools(
                    PromptTemplate(
                        system_prompt=system_prompt
                        + (
                            "\n\nPuedes consultar las herramientas disponibles para obtener "
                            "informacion adicional antes de responder. Si tienes suficiente contexto, "
                            "responde listo sin consultar herramientas."
                        ),
                        user_prompt=user_prompt,
                    ),
                    tools=self._knowledge_tools.defs(),
                    tool_handler=self._knowledge_tools.execute,
                    temperature=0.1,
                    max_tokens=2000,
                )
                invocations: list[dict[str, Any]] = [
                    {
                        "tool": r.name,
                        "args": {k: str(v)[:200] for k, v in r.args.items()},
                        "result_snippet": r.result_snippet[:500],
                        "found": "error" not in r.result_snippet.lower()[:20],
                    }
                    for r in records
                ]
                return (text.strip(), invocations)
            except Exception:
                _log.warning("agent.native_tools_failed", exc_info=True)
                pass

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
        invocations = []
        for _ in range(3):
            try:
                response = await self._llm_client.complete(
                    prompt=tool_prompt,
                    temperature=0.1,
                    max_tokens=200,
                )
            except Exception:
                _log.warning("agent.text_tools_call_failed", exc_info=True)
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
            not_found = result is None
            if not_found:
                collected.append(f"[TOOL: {tool_name}] Herramienta no encontrada")
            else:
                collected.append(f"[TOOL: {tool_name}]\n{result}")

            invocations.append(
                {
                    "tool": tool_name,
                    "args": {k: str(v)[:200] for k, v in tool_args.items()},
                    "result_snippet": (result or "herramienta no encontrada")[:500],
                    "found": not not_found,
                }
            )
            tool_prompt = PromptTemplate(
                system_prompt=tool_prompt.system_prompt,
                user_prompt=user_prompt + "\n\n" + collected[-1] + "\n\nResponde [CONTINUE] o [TOOL: ...]",
            )

        return ("\n\n".join(collected), invocations)

    async def _generate_reflection(
        self,
        *,
        phase: SpecPhase,
        session_type: str,
        is_completed: bool,
        current_iteration: int,
        validation: ValidationResult,
    ) -> str | None:
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
            _log.warning("agent.reflection_generation_failed", phase=phase.value, exc_info=True)
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


def _sanitize_context(context: Any) -> Any:
    replacements: dict[str, str] = {}
    for field_name in ("project_name", "project_description"):
        value = getattr(context, field_name, None)
        if isinstance(value, str) and value:
            replacements[field_name] = sanitize_user_instructions(value)
    return dataclasses.replace(context, **replacements) if replacements else context


_ROLE_LABELS: dict[ChatRole, str] = {
    ChatRole.USER: "Usuario",
    ChatRole.ASSISTANT: "Asistente",
    ChatRole.SYSTEM: "Sistema",
}


_MAX_HISTORY_WINDOW = 20
_MAX_HISTORY_TOKENS = 6000


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _format_chat_history(messages: list[MensajeChat]) -> str:
    """Formatea el historial de conversación para el prompt del LLM.

    Aplica ventana numérica y presupuesto de tokens: conserva los últimos N
    mensajes y decisiones anteriores, respetando un máximo de tokens estimados.
    Si se excede el presupuesto, descarta los mensajes más antiguos (excepto
    decisiones). Los mensajes de usuario se sanitizan contra inyección.
    """
    decisions: list[MensajeChat] = []
    recent: list[MensajeChat] = []

    if len(messages) <= _MAX_HISTORY_WINDOW:
        recent = list(messages)
    else:
        cut = len(messages) - _MAX_HISTORY_WINDOW
        decisions = [m for m in messages[:cut] if m.suggested_change is not None]
        recent = list(messages[cut:])

    header = "## Historial de conversacion\n\n"
    budget = _MAX_HISTORY_TOKENS - _count_tokens(header)

    def _format_one(msg: MensajeChat) -> str:
        role_label = _ROLE_LABELS.get(msg.role, msg.role.value)
        content = msg.content
        if msg.role == ChatRole.USER:
            content = sanitize_user_instructions(content)
        return f"**{role_label}:** {content}\n\n"

    lines = [header]
    used = _count_tokens(header)

    for msg in decisions:
        line = _format_one(msg)
        tokens = _count_tokens(line)
        if used + tokens > budget:
            break
        used += tokens
        lines.append(line)

    for msg in recent:
        line = _format_one(msg)
        tokens = _count_tokens(line)
        if used + tokens > budget:
            break
        used += tokens
        lines.append(line)

    result = "".join(lines)
    _log.debug("chat.history_tokens", messages_total=len(messages), used_tokens=used, budget=_MAX_HISTORY_TOKENS)
    return result


def _to_assistant_message(output: Any) -> MensajeChat:
    """Convierte la salida estructurada del LLM en un MensajeChat del asistente."""
    if not isinstance(output, RespuestaChatLLM):
        raise ValueError(f"El LLM devolvio un tipo inesperado: {type(output).__name__}. Se esperaba RespuestaChatLLM.")

    suggested_change: SugerenciaCambio | None = None
    if output.change_suggestion is not None:
        cs = output.change_suggestion
        suggested_change = SugerenciaCambio(
            id=IdGenerator.generate("plan_change"),
            section=cs.section,
            description=cs.description,
            diff=DiffCambio(before=cs.diff_before, after=cs.diff_after),
            rationale=cs.rationale,
        )

    return MensajeChat(
        id=ChatMessageId(IdGenerator.generate("chat_message")),
        role=ChatRole.ASSISTANT,
        content=output.content,
        suggested_change=suggested_change,
    )
