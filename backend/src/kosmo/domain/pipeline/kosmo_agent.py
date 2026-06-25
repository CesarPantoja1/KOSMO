from __future__ import annotations

import json
import time
from typing import Any

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.orchestrator_ports import PhaseMode, ToolResult
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase

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
        context_builder: Any,
        modes: dict[SpecPhase, PhaseMode],
        max_correction_cycles: int = 1,
    ) -> None:
        self._llm_client = llm_client
        self._context_builder = context_builder
        self._modes = modes
        self._max_correction_cycles = max_correction_cycles

    async def execute(
        self,
        phase: SpecPhase,
        context: Any,
    ) -> DiscoveryPhaseOutput:
        mode = self._modes.get(phase)
        if mode is None:
            raise ValueError(f"No hay modo para la fase {phase.value}")

        system_prompt = mode.system_prompt
        user_prompt = mode.build_user_prompt(context)

        reasoning_log: list[str] = []
        tool_results: list[ToolResult] = []
        generated_content: Any = None
        validation = ValidationResult(is_valid=False, errors=["No se generó contenido"])

        start_time = time.monotonic()

        for attempt in range(self._max_correction_cycles + 1):
            llm_response = await self._llm_client.complete(
                prompt=PromptTemplate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                ),
                temperature=_PHASE_TEMPERATURES.get(phase, 0.3),
                max_tokens=_PHASE_MAX_TOKENS.get(phase, 4096),
            )

            generated_content = self._parse_llm_response(llm_response.text)

            validation = mode.validate_output(generated_content)

            if validation.is_valid:
                total_ms = int((time.monotonic() - start_time) * 1000)
                metadata = GenerationMetadata(
                    llm_calls=attempt + 1,
                    total_tokens=llm_response.usage.total_tokens,
                    retry_count=attempt,
                    reasoning_log=reasoning_log,
                    tool_results=[
                        {"tool": r.tool_name, "output": str(r.output)} for r in tool_results
                    ],
                    generation_time_ms=total_ms,
                    model_used=llm_response.model,
                )
                return self._build_phase_output(generated_content, validation, metadata)

            reasoning_log.append(
                f"Intento {attempt + 1}: {len(validation.errors)} errores. "
                f"Corrigiendo: {validation.errors[:3]}"
            )

            user_prompt = mode.build_retry_prompt(user_prompt, validation.errors, attempt + 1)

        total_ms = int((time.monotonic() - start_time) * 1000)
        metadata = GenerationMetadata(
            llm_calls=self._max_correction_cycles + 1,
            total_tokens=0,
            retry_count=self._max_correction_cycles,
            reasoning_log=reasoning_log,
            tool_results=[{"tool": r.tool_name, "output": str(r.output)} for r in tool_results],
            generation_time_ms=total_ms,
        )
        return self._build_phase_output(generated_content, validation, metadata)

    def _parse_llm_response(self, text: str) -> Any:
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            if "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            return {"raw_text": text}

    def _build_phase_output(
        self,
        content: Any,
        validation: ValidationResult,
        metadata: GenerationMetadata,
    ) -> DiscoveryPhaseOutput:
        doc = self._extract_document(content)
        return DiscoveryPhaseOutput(
            discovery_document=doc,
            validation_result=validation,
            generation_metadata=metadata,
        )

    def _extract_document(self, content: Any) -> RichTextDocument:
        from kosmo.domain.sdd.document_converters import markdown_to_document

        if isinstance(content, str):
            return markdown_to_document(content)
        if isinstance(content, dict):
            text = content.get("document", content.get("raw_text", ""))  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            if text:
                return markdown_to_document(str(text))  # type: ignore[reportUnknownArgumentType]
            return markdown_to_document(str(content))  # type: ignore[reportUnknownArgumentType]
        return markdown_to_document(str(content))
