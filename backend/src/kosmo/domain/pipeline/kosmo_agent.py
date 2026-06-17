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
    SuggestedFeature,
    SuggestFeaturesOutput,
    ValidationResult,
)
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.contracts.sdd.ears import (
    EARSPattern,  # type: ignore[reportAttributeAccessIssue, reportUnknownVariableType]
    EARSRequirement,  # type: ignore[reportAttributeAccessIssue]
)
from kosmo.contracts.sdd.feature import Feature  # type: ignore[reportAttributeAccessIssue]
from kosmo.domain.sdd.document_converters import slugify_spanish
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
        phase: SpecPhase,
        context: Any,
    ) -> DiscoveryPhaseOutput | FeaturesPhaseOutput | EARSPhaseOutput:
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
        context: SuggestFeaturesContext,
    ) -> SuggestFeaturesOutput:
        suggest_prompt = (
            "Eres un diseñador de producto experto.\n"
            "A continuación se presenta un Documento de Descubrimiento y una lista de\n"
            "características ya existentes. Tu tarea es sugerir EXACTAMENTE 3 nuevas\n"
            "características que NO dupliquen las ya existentes.\n\n"
            "Respondé ÚNICAMENTE con JSON:\n"
            "```json\n"
            '{"suggestions": [\n'
            '  {"title": "...", "description": "...", "rationale": "...",\n'
            '   "inferred_from": ["..."]}\n'
            "]}\n"
            "```\n\n"
        )
        from kosmo.domain.sdd.document_converters import document_to_markdown

        suggest_prompt += "## Documento de Descubrimiento\n\n"
        suggest_prompt += document_to_markdown(context.discovery_document)

        if context.existing_feature_titles:
            titles = ", ".join(context.existing_feature_titles)
            suggest_prompt += f"\n\n## Características ya existentes (NO duplicar)\n\n{titles}"

        suggest_prompt += (
            f"\n\nLa primera sugerencia será C{context.next_feature_number:02d}."
            f"\nGenerá exactamente 3 sugerencias. Nada de texto antes o después del JSON."
        )

        llm_response = await self._llm_client.complete(
            prompt=PromptTemplate(
                system_prompt=suggest_prompt,
                user_prompt="Generá 3 sugerencias de características.",
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
    ) -> list[SuggestedFeature]:
        from kosmo.contracts.pipeline.phase_outputs import SuggestedFeature

        suggestions: list[SuggestedFeature] = []
        if isinstance(data, dict) and "suggestions" in data:
            items = data["suggestions"]  # type: ignore[reportUnknownVariableType]
        elif isinstance(data, list):
            items = data  # type: ignore[reportUnknownVariableType]
        else:
            return []

        for i, item in enumerate(items[:3]):  # type: ignore[reportUnknownVariableType]
            number = context.next_feature_number + i
            suggestions.append(
                SuggestedFeature(
                    number=number,
                    title=item.get("title", f"Caracteristica {number}"),  # type: ignore[reportUnknownArgumentType, reportUnknownMemberType]
                    description=item.get("description", ""),  # type: ignore[reportUnknownArgumentType, reportUnknownMemberType]
                    rationale=item.get("rationale", ""),  # type: ignore[reportUnknownArgumentType, reportUnknownMemberType]
                    inferred_from=item.get("inferred_from", []),  # type: ignore[reportUnknownArgumentType, reportUnknownMemberType]
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
            feature_id = reqs[0].feature_id if reqs else IdGenerator.generate("feature")  # type: ignore[reportArgumentType, reportAttributeAccessIssue]
            feature_number = reqs[0].feature_number if reqs else 1  # type: ignore[reportAttributeAccessIssue]
            return EARSPhaseOutput(
                feature_id=feature_id,  # type: ignore[reportArgumentType]
                feature_number=feature_number,  # type: ignore[reportUnknownArgumentType]
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
            text = content.get("document", content.get("raw_text", ""))  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            if text:
                return markdown_to_document(str(text))  # type: ignore[reportUnknownArgumentType]
            return markdown_to_document(str(content))  # type: ignore[reportUnknownArgumentType]
        return markdown_to_document(str(content))

    def _extract_features(
        self, content: Any
    ) -> list[Feature]:
        features: list[Feature] = []
        items: list[dict[str, Any]] = []

        if isinstance(content, dict):
            items = content.get("features", [])  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        elif isinstance(content, list):
            items = content  # type: ignore[reportUnknownVariableType]

        seen_slugs: set[str] = set()
        for i, item in enumerate(items, start=1):  # type: ignore[reportUnknownVariableType]
            raw_slug = item.get("slug") or slugify_spanish(item.get("title", f"c{i:02d}"))  # type: ignore[reportUnknownArgumentType]
            slug = _unique_slug(raw_slug, seen_slugs)
            seen_slugs.add(slug)
            features.append(
                Feature(
                    id=IdGenerator.generate("feature"),  # type: ignore[reportArgumentType]
                    number=item.get("number", i),  # type: ignore[reportUnknownArgumentType]
                    title=item.get("title", f"Caracteristica {i}"),  # type: ignore[reportUnknownArgumentType]
                    slug=slug,  # type: ignore[reportCallIssue]
                    description=item.get("description", ""),  # type: ignore[reportUnknownArgumentType]
                    rationale=item.get("rationale", ""),  # type: ignore[reportUnknownArgumentType]
                    inferred_from=item.get("inferred_from", []),  # type: ignore[reportUnknownArgumentType]
                )
            )
        return features

    def _extract_requirements(
        self, content: Any
    ) -> list[EARSRequirement]:
        requirements: list[EARSRequirement] = []
        items: list[dict[str, Any]] = []

        if isinstance(content, dict):
            items = content.get("requirements", [])  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        elif isinstance(content, list):
            items = content  # type: ignore[reportUnknownVariableType]

        for i, item in enumerate(items, start=1):  # type: ignore[reportUnknownVariableType]
            pattern_str = item.get("pattern", "ubiquitous")  # type: ignore[reportUnknownArgumentType]
            try:
                pattern = EARSPattern(pattern_str)  # type: ignore[reportUnknownVariableType, reportCallIssue]
            except ValueError:
                pattern = EARSPattern.ubiquitous  # type: ignore[reportUnknownMemberType]

            feature_number = item.get("feature_number", 1)  # type: ignore[reportUnknownArgumentType]
            requirement_number = item.get("requirement_number", i)  # type: ignore[reportUnknownArgumentType]

            acceptance_criteria = []
            for ac in item.get("acceptance_criteria", []):  # type: ignore[reportUnknownArgumentType]
                if isinstance(ac, dict):
                    from kosmo.contracts.sdd.document import AcceptanceCriterion

                    acceptance_criteria.append(  # type: ignore[reportUnknownMemberType]
                        AcceptanceCriterion(
                            given=ac.get("given", ""),  # type: ignore[reportUnknownArgumentType]
                            when=ac.get("when", ""),  # type: ignore[reportUnknownArgumentType]
                            then=ac.get("then", ""),  # type: ignore[reportUnknownArgumentType]
                        )
                    )

            requirements.append(
                EARSRequirement(  # type: ignore[reportCallIssue]
                    id=IdGenerator.generate("requirement"),  # type: ignore[reportArgumentType]
                    feature_id=item.get("feature_id", IdGenerator.generate("feature")),  # type: ignore[reportArgumentType, reportUnknownArgumentType]
                    feature_number=feature_number,  # type: ignore[reportCallIssue]
                    requirement_number=requirement_number,  # type: ignore[reportCallIssue]
                    pattern=pattern,  # type: ignore[reportCallIssue]
                    trigger=item.get("trigger", ""),  # type: ignore[reportUnknownArgumentType]
                    system=item.get("system", "El sistema"),  # type: ignore[reportUnknownArgumentType]
                    response=item.get("response", ""),  # type: ignore[reportUnknownArgumentType]
                    source_statement=item.get("source_statement", ""),  # type: ignore[reportUnknownArgumentType]
                    rationale=item.get("rationale", ""),  # type: ignore[reportUnknownArgumentType]
                    traceability=item.get("traceability", []),  # type: ignore[reportUnknownArgumentType]
                    acceptance_criteria=acceptance_criteria,  # type: ignore[reportUnknownArgumentType]
                )
            )
        return requirements

    def _requirements_to_markdown(self, requirements: list[EARSRequirement]) -> str:  # type: ignore[reportAttributeAccessIssue]
        from kosmo.contracts.sdd.document import EARSPatternLabel

        grouped: dict[EARSPattern, list[EARSRequirement]] = {}  # type: ignore[reportUnknownVariableType]
        for req in requirements:
            grouped.setdefault(req.pattern, []).append(req)  # type: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownArgumentType]

        lines: list[str] = []
        for pattern in EARSPattern:  # type: ignore[reportUnknownVariableType]
            reqs = grouped.get(pattern, [])  # type: ignore[reportUnknownArgumentType]
            if not reqs:
                continue
            label = EARSPatternLabel[pattern.value]  # type: ignore[reportUnknownMemberType]
            lines.append(f"### {label.value}")
            lines.append("")
            for req in reqs:
                lines.append(f"- {req.display_id}: {req.source_statement}")  # type: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
                if req.acceptance_criteria:  # type: ignore[reportAttributeAccessIssue]
                    for ac in req.acceptance_criteria:  # type: ignore[reportAttributeAccessIssue]
                        lines.append(
                            f"  - **Criterio**: Dado {ac.given}, Cuando {ac.when}, "  # type: ignore[reportUnknownMemberType]
                            f"Entonces {ac.then}"  # type: ignore[reportUnknownMemberType]
                        )
            lines.append("")

        return "\n".join(lines)


def _unique_slug(base: str, existing: set[str]) -> str:
    slug = base
    counter = 2
    while slug in existing:
        slug = f"{base}-{counter}"
        counter += 1
    return slug
