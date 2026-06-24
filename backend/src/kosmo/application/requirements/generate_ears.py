from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.phase_contexts import EARSPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
    GenerationMetadata,
)
from kosmo.contracts.sdd.ears import EARSRequirement, EARSPattern
from kosmo.contracts.sdd.document import AcceptanceCriterion
from kosmo.contracts.sdd.errors import LLMInvocationError
from kosmo.contracts.sdd.ids import ProjectId, FeatureId, RequirementId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.domain.pipeline.phase_modes.ears_mode import EARSMode
from kosmo.domain.sdd.id_generator import IdGenerator


@dataclass(frozen=True)
class GenerateEARSInput:
    project_id: ProjectId
    feature_id: FeatureId


@dataclass(frozen=True)
class GenerateEARSOutput:
    project_id: ProjectId
    feature_id: FeatureId
    requirements: list[EARSRequirement]
    phase_output: EARSPhaseOutput


class GenerateEARSUseCase:
    """Caso de uso: genera los requisitos EARS de una característica mediante IA.

    Orquesta la generación:
    1. Verifica que proyecto y característica existan.
    2. Obtiene el documento de descubrimiento.
    3. Construye el contexto EARSPhaseContext.
    4. Delega al LLM la generación usando EARSMode.
    5. Valida la estructura y reglas (sintaxis y calidad).
    6. Convierte el resultado a entidades EARSRequirement y a Markdown.
    7. Persiste el Markdown en el RequirementRepository.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        llm_client: LLMClient,
    ) -> None:
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._llm_client = llm_client

    async def execute(self, input_data: GenerateEARSInput) -> GenerateEARSOutput:
        from kosmo.contracts.sdd.errors import (
            DocumentNotFoundError,
            ProjectNotFoundError,
            FeatureNotFoundError,
        )

        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            )

        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None or feature.project_id != input_data.project_id:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            )

        discovery_doc = await self._document_repo.get_discovery(input_data.project_id)
        if discovery_doc is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            )

        mode = EARSMode()
        context = EARSPhaseContext(
            discovery_document=discovery_doc,
            feature=feature,
            feature_number=feature.number,
        )

        system_prompt = mode.system_prompt
        user_prompt = mode.build_user_prompt(context)

        max_retries = 2
        last_errors: list[str] = []

        try:
            for attempt in range(max_retries + 1):
                llm_response = await self._llm_client.complete(
                    prompt=PromptTemplate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    ),
                    temperature=0.2,
                    max_tokens=4096,
                )

                generated_content = self._parse_llm_response(llm_response.text)
                validation = mode.validate_output(generated_content)

                if validation.is_valid:
                    reqs_data = self._extract_requirements_list(generated_content)
                    requirements = self._build_requirements(reqs_data, input_data.feature_id, feature.number)

                    markdown_str = self._requirements_to_markdown(requirements)
                    await self._requirement_repo.save(input_data.feature_id, markdown_str)

                    metadata = GenerationMetadata(
                        llm_calls=attempt + 1,
                        total_tokens=llm_response.usage.total_tokens,
                        retry_count=attempt,
                        model_used=llm_response.model,
                    )

                    return GenerateEARSOutput(
                        project_id=input_data.project_id,
                        feature_id=input_data.feature_id,
                        requirements=requirements,
                        phase_output=EARSPhaseOutput(
                            feature_id=input_data.feature_id,
                            feature_number=feature.number,
                            requirements=requirements,
                            requirements_markdown=markdown_str,
                            validation_result=validation,
                            generation_metadata=metadata,
                        ),
                    )

                last_errors = validation.errors
                user_prompt = mode.build_retry_prompt(user_prompt, last_errors, attempt + 1)

            raise LLMInvocationError(
                detail=(
                    f"No se pudieron generar requisitos válidos después de "
                    f"{max_retries + 1} intentos: {'; '.join(last_errors)}"
                ),
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            )

        except LLMInvocationError:
            raise
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al generar requisitos EARS: {exc}",
                instance=f"/api/v1/projects/{input_data.project_id}/features/{input_data.feature_id}/requirements",
            ) from exc

    @staticmethod
    def _parse_llm_response(text: str) -> Any:
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

    @staticmethod
    def _extract_requirements_list(content: Any) -> list[dict[str, Any]]:  # pyright: ignore[reportExplicitAny]
        if isinstance(content, dict):
            raw: object = content.get("requirements", [])  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            if isinstance(raw, list):
                return raw  # type: ignore[reportReturnType]
        if isinstance(content, list):
            return content  # type: ignore[reportReturnType]
        return []

    @staticmethod
    def _build_requirements(
        reqs_data: list[dict[str, Any]],  # pyright: ignore[reportExplicitAny]
        feature_id: FeatureId,
        feature_number: int,
    ) -> list[EARSRequirement]:
        requirements: list[EARSRequirement] = []
        
        for i, item in enumerate(reqs_data, start=1):
            pattern_str = item.get("pattern", "ubiquitous")
            try:
                pattern = EARSPattern(pattern_str.lower())
            except ValueError:
                pattern = EARSPattern.ubiquitous
                
            raw_ac = item.get("acceptance_criteria", [])
            criteria = []
            if isinstance(raw_ac, list):
                for ac in raw_ac:
                    if isinstance(ac, dict):
                        criteria.append(
                            AcceptanceCriterion(
                                given=str(ac.get("given", "")),
                                when=str(ac.get("when", "")),
                                then=str(ac.get("then", "")),
                            )
                        )
            
            requirements.append(
                EARSRequirement(
                    id=RequirementId(IdGenerator.generate("req")),
                    feature_id=feature_id,
                    feature_number=feature_number,
                    requirement_number=i,
                    pattern=pattern,
                    trigger=str(item.get("trigger", "")),
                    system=str(item.get("system", "")),
                    response=str(item.get("response", "")),
                    source_statement=str(item.get("source_statement", "")),
                    rationale=str(item.get("rationale", "")),
                    traceability=item.get("traceability", []) if isinstance(item.get("traceability"), list) else [],
                    acceptance_criteria=criteria,
                )
            )

        return requirements

    @staticmethod
    def _requirements_to_markdown(reqs: list[EARSRequirement]) -> str:
        lines = [
            "## Requisitos EARS",
            "",
            "| ID | Categoría | Requisito (Source Statement) | Justificación |",
            "|---|---|---|---|",
        ]
        for r in reqs:
            # Escape pipes to avoid breaking the markdown table
            stmt = r.source_statement.replace("|", "\\|")
            rationale = r.rationale.replace("|", "\\|")
            lines.append(f"| **{r.display_id}** | {r.pattern.value} | {stmt} | {rationale} |")
        
        lines.append("")
        lines.append("### Criterios de Aceptación")
        lines.append("")
        for r in reqs:
            if r.acceptance_criteria:
                lines.append(f"#### {r.display_id}")
                for idx, ac in enumerate(r.acceptance_criteria, 1):
                    lines.append(f"**Criterio {idx}:**")
                    lines.append(f"- **Dado**: {ac.given}")
                    lines.append(f"- **Cuando**: {ac.when}")
                    lines.append(f"- **Entonces**: {ac.then}")
                lines.append("")
        
        return "\n".join(lines).strip()


class GetRequirementsUseCase:
    """Caso de uso: obtiene los requisitos de una característica en formato Markdown."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo

    async def execute(self, project_id: ProjectId, feature_id: FeatureId) -> str | None:
        from kosmo.contracts.sdd.errors import ProjectNotFoundError, FeatureNotFoundError

        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(project_id),
                instance=f"/api/v1/projects/{project_id}/features/{feature_id}/requirements",
            )

        feature = await self._feature_repo.by_id(feature_id)
        if feature is None or feature.project_id != project_id:
            raise FeatureNotFoundError(
                feature_id=str(feature_id),
                instance=f"/api/v1/projects/{project_id}/features/{feature_id}/requirements",
            )

        return await self._requirement_repo.by_feature_id(feature_id)
