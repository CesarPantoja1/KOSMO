from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog

from kosmo.application.pipeline.prompt_enricher import PromptEnricher
from kosmo.application.pipeline.session_recorder import SessionRecorder
from kosmo.application.pipeline.tool_resolver import ToolResolver
from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.orchestrator_ports import PhaseMode
from kosmo.contracts.pipeline.phase_outputs import GenerationMetadata, ValidationResult
from kosmo.contracts.sdd.ids import ProjectId

_log = structlog.get_logger(__name__)


class GenerationLoop:
    """Ejecuta el loop de generacion de un skill: enrich, tools, retries y persistencia."""

    def __init__(
        self,
        llm_client: LLMClient,
        max_iterations: int,
        prompt_enricher: PromptEnricher,
        tool_resolver: ToolResolver,
        session_recorder: SessionRecorder,
    ) -> None:
        self._llm_client = llm_client
        self._max_iterations = max_iterations
        self._prompt_enricher = prompt_enricher
        self._tool_resolver = tool_resolver
        self._session_recorder = session_recorder

    async def run(
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
        base_user_prompt = mode.build_user_prompt(context)

        needs_enrichment = getattr(mode, "requires_enrichment", True)

        if needs_enrichment:
            system_prompt = await self._prompt_enricher.enrich(
                system_prompt, base_user_prompt, project_id, phase=mode.phase_name
            )

        knowledge_context: str = ""
        tool_invocations: list[dict[str, Any]] = []
        reason_entries: list[str] = []
        if needs_enrichment:
            knowledge_context, tool_invocations, reason_entries = await self._tool_resolver.resolve(
                system_prompt, base_user_prompt, project_id
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
                _log.warning("agent.llm_call_failed", skill_name=skill_name, iteration=iteration, exc_info=True)
                break

            _log.info(
                "agent.llm_call_ok",
                skill_name=skill_name,
                iteration=iteration,
                output_type=str(type(last_output)),  # type: ignore[reportUnknownArgumentType]
                output_preview=str(last_output)[:200],
            )
            llm_calls += 1
            last_validation = mode.validate_output(last_output, context=context)
            _log.info("agent.validation_done", is_valid=last_validation.is_valid, errors=last_validation.errors[:5])

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

                if needs_enrichment and project_id is not None:
                    await self._session_recorder.record(
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

                result = mode.build_output(last_output, last_validation, metadata, context=context)
                _log.info("agent.build_output_done", result_type=str(type(result)))  # type: ignore[reportUnknownArgumentType]
                return result

            delay_s = min(1.0 * (2 ** (iteration - 1)), 5.0)
            await asyncio.sleep(delay_s)

            retry_context = ""
            if needs_enrichment and last_validation.errors and iteration < self._max_iterations:
                error_list = "; ".join(last_validation.errors[:5])
                retry_system_prompt = (
                    system_prompt + "\n\nLa validacion del contenido generado fallo "
                    "con los siguientes errores. Puedes consultar herramientas "
                    "para corregir antes de reintentar."
                )
                retry_user_prompt = f"Errores de validacion: {error_list}"
                try:
                    retry_context, retry_records = await self._tool_resolver.resolve_knowledge_tools(
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

        if needs_enrichment and project_id is not None:
            await self._session_recorder.record(
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
