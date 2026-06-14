from __future__ import annotations

import json
import time
from typing import Any

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.orchestrator_ports import PhaseMode, ToolResult
from kosmo.contracts.pipeline.phase_contexts import (
    SuggestFeaturesContext,
)
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    EARSPhaseOutput,
    FeaturesPhaseOutput,
    GenerationMetadata,
    SuggestFeaturesOutput,
    ValidationResult,
)
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState
from kosmo.contracts.sdd.document import FeatureStatus, RichTextDocument, SpecPhase
from kosmo.contracts.sdd.ears import EARSPattern, EARSRequirement
from kosmo.contracts.sdd.feature import Feature
from kosmo.domain.sdd.id_generator import IdGenerator

_PHASE_TEMPERATURES: dict[SpecPhase, float] = {
    SpecPhase.DESCUBRIMIENTO: 0.3,
    SpecPhase.CARACTERISTICAS: 0.2,
    SpecPhase.REQUISITOS: 0.1,
}

_PHASE_MAX_TOKENS: dict[SpecPhase, int] = {
    SpecPhase.DESCUBRIMIENTO: 8192,
    SpecPhase.CARACTERISTICAS: 4096,
    SpecPhase.REQUISITOS: 4096,
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
        pipeline_state: KOSMOPipelineState,
    ) -> DiscoveryPhaseOutput | FeaturesPhaseOutput | EARSPhaseOutput:
        phase = pipeline_state.current_phase
        mode = self._modes.get(phase)
        if mode is None:
            raise ValueError(f"No hay modo para la fase {phase.value}")

        context = await self._context_builder.build_context(pipeline_state, phase)
        system_prompt = mode.system_prompt
        user_prompt = mode.build_user_prompt(context)

        reasoning_log: list[str] = []
        tool_results: list[ToolResult] = []
        generated_content: Any = None
        validation = ValidationResult(is_valid=False, errors=["No se generó contenido"])

        start_time = time.monotonic()

        for attempt in range(self._max_correction_cycles + 1):
            start_call = time.monotonic()
            llm_response = await self._llm_client.complete(
                prompt=PromptTemplate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                ),
                temperature=_PHASE_TEMPERATURES.get(phase, 0.3),
                max_tokens=_PHASE_MAX_TOKENS.get(phase, 4096),
            )
            int((time.monotonic() - start_call) * 1000)

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
                return self._build_phase_output(phase, generated_content, validation, metadata)

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
        return self._build_phase_output(phase, generated_content, validation, metadata)

    async def execute_suggest(
        self,
        pipeline_state: KOSMOPipelineState,
    ) -> SuggestFeaturesOutput:
        context = await self._context_builder.build_suggest_features_context(pipeline_state)

        features_mode = self._modes.get(SpecPhase.CARACTERISTICAS)
        if features_mode is None:
            raise ValueError("No hay modo para la fase de Caracteristicas")

        suggest_prompt = (
            f"{features_mode.system_prompt}\n\n"
            f"## Modo: Sugerir 3 caracteristicas adicionales\n\n"
            f"Genera EXACTAMENTE 3 sugerencias que NO dupliquen las caracteristicas ya existentes.\n"
            f"La primera sugerencia sera C{context.next_feature_number:02d}.\n\n"
            f"Documento de Descubrimiento:\n\n"
        )
        from kosmo.domain.sdd.document_converters import document_to_markdown

        suggest_prompt += document_to_markdown(context.discovery_document)

        if context.existing_feature_titles:
            titles = ", ".join(context.existing_feature_titles)
            suggest_prompt += f"\n\nCaracteristicas ya existentes (NO duplicar): {titles}"

        llm_response = await self._llm_client.complete(
            prompt=PromptTemplate(
                system_prompt=suggest_prompt,
                user_prompt="Genera 3 sugerencias de caracteristicas.",
            ),
            temperature=0.4,
        )

        suggestions_data = self._parse_llm_response(llm_response.text)
        suggestions = self._parse_suggestions(suggestions_data, context)

        return SuggestFeaturesOutput(
            suggestions=suggestions,
            excluded_titles=context.existing_feature_titles,
            domain_inferred=context.discovery_document.sections[0].text
            if context.discovery_document.sections
            else "",
        )

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

    def _parse_suggestions(
        self,
        data: Any,
        context: SuggestFeaturesContext,
    ) -> list:
        from kosmo.contracts.pipeline.phase_outputs import SuggestedFeature

        suggestions: list[SuggestedFeature] = []
        if isinstance(data, dict) and "suggestions" in data:
            items = data["suggestions"]
        elif isinstance(data, list):
            items = data
        else:
            return []

        for i, item in enumerate(items[:3]):
            number = context.next_feature_number + i
            suggestions.append(
                SuggestedFeature(
                    number=number,
                    title=item.get("title", f"Caracteristica {number}"),
                    description=item.get("description", ""),
                    rationale=item.get("rationale", ""),
                    inferred_from=item.get("inferred_from", []),
                )
            )
        return suggestions

    def _build_phase_output(
        self,
        phase: SpecPhase,
        content: Any,
        validation: ValidationResult,
        metadata: GenerationMetadata,
    ) -> DiscoveryPhaseOutput | FeaturesPhaseOutput | EARSPhaseOutput:
        if phase == SpecPhase.DESCUBRIMIENTO:
            doc = self._extract_document(content)
            return DiscoveryPhaseOutput(
                discovery_document=doc,
                validation_result=validation,
                generation_metadata=metadata,
            )
        elif phase == SpecPhase.CARACTERISTICAS:
            features = self._extract_features(content)
            return FeaturesPhaseOutput(
                features=features,
                validation_result=validation,
                generation_metadata=metadata,
            )
        elif phase == SpecPhase.REQUISITOS:
            reqs = self._extract_requirements(content)
            feature_id = reqs[0].feature_id if reqs else IdGenerator.generate("feature")
            feature_number = reqs[0].feature_number if reqs else 1
            return EARSPhaseOutput(
                feature_id=feature_id,
                feature_number=feature_number,
                requirements=reqs,
                requirements_markdown=self._requirements_to_markdown(reqs),
                validation_result=validation,
                generation_metadata=metadata,
            )
        else:
            raise ValueError(f"Fase no soportada: {phase.value}")

    def _extract_document(self, content: Any) -> RichTextDocument:
        from kosmo.domain.sdd.document_converters import markdown_to_document

        if isinstance(content, str):
            return markdown_to_document(content)
        if isinstance(content, dict):
            text = content.get("document", content.get("raw_text", ""))
            if text:
                return markdown_to_document(str(text))
            return markdown_to_document(str(content))
        return markdown_to_document(str(content))

    def _extract_features(self, content: Any) -> list[Feature]:
        features: list[Feature] = []
        items: list[dict] = []

        if isinstance(content, dict):
            items = content.get("features", [])
        elif isinstance(content, list):
            items = content

        for i, item in enumerate(items, start=1):
            features.append(
                Feature(
                    id=IdGenerator.generate("feature"),
                    number=item.get("number", i),
                    title=item.get("title", f"Caracteristica {i}"),
                    slug=item.get("slug", item.get("title", f"c{i:02d}").lower().replace(" ", "-")),
                    description=item.get("description", ""),
                    status=FeatureStatus.borrador,
                    rationale=item.get("rationale", ""),
                    inferred_from=item.get("inferred_from", []),
                )
            )
        return features

    def _extract_requirements(self, content: Any) -> list[EARSRequirement]:
        requirements: list[EARSRequirement] = []
        items: list[dict] = []

        if isinstance(content, dict):
            items = content.get("requirements", [])
        elif isinstance(content, list):
            items = content

        for i, item in enumerate(items, start=1):
            pattern_str = item.get("pattern", "ubiquitous")
            try:
                pattern = EARSPattern(pattern_str)
            except ValueError:
                pattern = EARSPattern.ubiquitous

            feature_number = item.get("feature_number", 1)
            requirement_number = item.get("requirement_number", i)

            acceptance_criteria = []
            for ac in item.get("acceptance_criteria", []):
                if isinstance(ac, dict):
                    from kosmo.contracts.sdd.document import AcceptanceCriterion

                    acceptance_criteria.append(
                        AcceptanceCriterion(
                            given=ac.get("given", ""),
                            when=ac.get("when", ""),
                            then=ac.get("then", ""),
                        )
                    )

            requirements.append(
                EARSRequirement(
                    id=IdGenerator.generate("requirement"),
                    feature_id=item.get("feature_id", IdGenerator.generate("feature")),
                    feature_number=feature_number,
                    requirement_number=requirement_number,
                    pattern=pattern,
                    trigger=item.get("trigger", ""),
                    system=item.get("system", "El sistema"),
                    response=item.get("response", ""),
                    source_statement=item.get("source_statement", ""),
                    rationale=item.get("rationale", ""),
                    traceability=item.get("traceability", []),
                    acceptance_criteria=acceptance_criteria,
                )
            )
        return requirements

    def _requirements_to_markdown(self, requirements: list[EARSRequirement]) -> str:
        from kosmo.contracts.sdd.document import EARSPatternLabel

        grouped: dict[EARSPattern, list[EARSRequirement]] = {}
        for req in requirements:
            grouped.setdefault(req.pattern, []).append(req)

        lines: list[str] = []
        for pattern in EARSPattern:
            reqs = grouped.get(pattern, [])
            if not reqs:
                continue
            label = EARSPatternLabel[pattern.value]
            lines.append(f"### {label.value}")
            lines.append("")
            for req in reqs:
                lines.append(f"- {req.display_id}: {req.source_statement}")
                if req.acceptance_criteria:
                    for ac in req.acceptance_criteria:
                        lines.append(
                            f"  - **Criterio**: Dado {ac.given}, Cuando {ac.when}, "
                            f"Entonces {ac.then}"
                        )
            lines.append("")

        return "\n".join(lines)
