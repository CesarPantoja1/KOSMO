from __future__ import annotations

import json
import time
from typing import Any

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.orchestrator_ports import PhaseMode
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.domain.pipeline.tool_registry import ToolRegistry

_REACT_FORMAT_INSTRUCTIONS = (
    "FORMATO DE RESPUESTA: Responde UNICAMENTE en JSON con uno de estos dos formatos.\n\n"
    "1. Para usar una herramienta:\n"
    '   {{"reasoning": "por que necesitas esta herramienta", '
    '"action": "nombre_herramienta", "input": {{"param": "valor"}}}}\n\n'
    "2. Para dar la respuesta final:\n"
    '   {{"reasoning": "por que el trabajo esta completo", "final": true, '
    '"output": "documento completo en markdown"}}\n\n'
    "REGLAS:\n"
    "- NO escribas texto fuera del JSON.\n"
    "- Usa herramientas para verificar tu trabajo antes de responder.\n"
    "- Si una validacion falla, usa el feedback para corregir.\n"
)

_PHASE_TEMPERATURES: dict[SpecPhase, float] = {
    SpecPhase.DESCUBRIMIENTO: 0.3,
}

_PHASE_MAX_TOKENS: dict[SpecPhase, int] = {
    SpecPhase.DESCUBRIMIENTO: 8192,
}


class KOSMOAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        modes: dict[SpecPhase, PhaseMode] | None = None,
        max_iterations: int = 5,
        skill_registry: SkillRegistry | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._registry = registry
        self._modes: dict[SpecPhase, PhaseMode] = modes or {}
        self._max_iterations = max_iterations
        self._skill_registry: SkillRegistry | None = skill_registry

    async def execute_with_skill(
        self,
        skill_name: str,
        context: Any,
    ) -> Any:
        if self._skill_registry is None:
            raise ValueError("SkillRegistry no configurado")
        mode = self._skill_registry.resolve(skill_name)
        # Reuse el mismo bucle ReAct con el modo resuelto
        return await self._execute_loop(mode, context)

    async def execute(
        self,
        phase: SpecPhase,
        context: Any,
    ) -> Any:
        mode = self._modes.get(phase)
        if mode is None:
            raise ValueError(f"No hay modo para la fase {phase.value}")
        return await self._execute_loop(mode, context)

    async def _execute_loop(self, mode: PhaseMode, context: Any) -> Any:
        phase = mode.phase_name
        system_prompt = self._build_react_system_prompt(mode)
        base_user_prompt = mode.build_user_prompt(context)

        trace_entries: list[str] = []
        tool_results_entries: list[dict[str, str]] = []
        last_output: Any = None
        last_validation = ValidationResult(is_valid=False, errors=["No se genero contenido"])

        start_time = time.monotonic()

        conversation: list[str] = [base_user_prompt]

        for iteration in range(1, self._max_iterations + 1):
            current_user_prompt = "\n\n".join(conversation)

            temperature = _PHASE_TEMPERATURES.get(phase, 0.3)
            max_tokens = _PHASE_MAX_TOKENS.get(phase, 4096)

            llm_response = await self._llm_client.complete(
                prompt=PromptTemplate(
                    system_prompt=system_prompt,
                    user_prompt=current_user_prompt,
                ),
                temperature=temperature,
                max_tokens=max_tokens,
            )
            conversation.append(llm_response.text)

            parsed = self._parse_react_response(llm_response.text)

            # Final answer
            if parsed.get("final"):
                last_output = parsed.get("output", "")
                last_validation = mode.validate_output(last_output)

                trace_entries.append(
                    f"Paso {iteration}: respuesta final. "
                    f"Valido={last_validation.is_valid}, "
                    f"errores={len(last_validation.errors)}"
                )

                if last_validation.is_valid:
                    total_ms = int((time.monotonic() - start_time) * 1000)
                    metadata = GenerationMetadata(
                        llm_calls=iteration,
                        total_tokens=llm_response.usage.total_tokens,
                        retry_count=iteration - 1,
                        reasoning_log=trace_entries,
                        tool_results=tool_results_entries,
                        generation_time_ms=total_ms,
                        model_used=llm_response.model,
                    )
                    return mode.build_output(last_output, last_validation, metadata)

                feedback = (
                    "## Feedback de validacion\n\n"
                    "El documento tiene los siguientes errores:\n"
                )
                for err in last_validation.errors:
                    feedback += f"- {err}\n"
                feedback += "\nCorrige estos problemas y genera el documento completo nuevamente."
                conversation.append(feedback)
                continue

            # Tool call
            tool_name = parsed.get("action", "")
            tool_input = parsed.get("input", {})
            reasoning = parsed.get("reasoning", "")

            trace_entries.append(
                f"Paso {iteration}: llamada a herramienta '{tool_name}'. "
                f"Razonamiento: {reasoning[:120]}"
            )

            result = self._registry.execute(tool_name, tool_input)
            tool_results_entries.append(
                {"tool": tool_name, "output": json.dumps(result, default=str)}
            )

            observation = json.dumps(result, default=str)
            conversation.append(
                f"## Resultado de la herramienta '{tool_name}'\n\n{observation}"
            )

        # Max iterations reached
        total_ms = int((time.monotonic() - start_time) * 1000)
        metadata = GenerationMetadata(
            llm_calls=self._max_iterations,
            total_tokens=0,
            retry_count=self._max_iterations - 1,
            reasoning_log=trace_entries,
            tool_results=tool_results_entries,
            generation_time_ms=total_ms,
        )
        return mode.build_output(last_output, last_validation, metadata)

    def _build_react_system_prompt(self, mode: PhaseMode) -> str:
        tools_desc = self._registry.describe_tools(mode.available_tools)
        return (
            f"{mode.system_prompt}\n\n"
            f"## Herramientas disponibles\n\n"
            f"{tools_desc}\n\n"
            f"{_REACT_FORMAT_INSTRUCTIONS}"
        )

    def _parse_react_response(self, text: str) -> dict[str, Any]:
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)  # type: ignore[reportUnknownVariableType]
            if "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)  # type: ignore[reportUnknownVariableType]
            return json.loads(text.strip())  # type: ignore[reportUnknownVariableType]
        except (json.JSONDecodeError, IndexError, TypeError):
            return {
                "final": True,
                "output": text,
                "reasoning": "Respuesta no-JSON, tratada como final",
            }
