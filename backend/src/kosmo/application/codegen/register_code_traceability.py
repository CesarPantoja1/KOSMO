from __future__ import annotations

import re
from dataclasses import dataclass, field

from kosmo.contracts.consistency import TraceabilityRepository
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import RequirementRepository

_REQ_CODE_RE = re.compile(r"REQ-\d+\.\d+", re.IGNORECASE)


def format_requirement_key(feature_id: FeatureId | str, req_code: str) -> str:
    """Formatea la clave estable del requisito con el formato feature_id:REQ-display_id."""
    f_str = str(feature_id).strip()
    c_str = req_code.strip()
    if c_str.startswith(f"{f_str}:"):
        return c_str
    return f"{f_str}:{c_str}"


def _is_test_file(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/").lower()
    return (
        normalized.startswith("tests/") or "/tests/" in normalized or ".test." in normalized or ".spec." in normalized
    )


@dataclass(frozen=True)
class RequirementCodeMapping:
    requirement_code: str
    code_files: tuple[str, ...] = field(default_factory=tuple)
    test_files: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RegisterCodeTraceabilityInput:
    feature_id: FeatureId
    generated_files: tuple[str, ...] = field(default_factory=tuple)
    mappings: tuple[RequirementCodeMapping, ...] = field(default_factory=tuple)
    origin: str = "codegen"
    clean_previous: bool = True


@dataclass(frozen=True)
class RegisterCodeTraceabilityOutput:
    feature_id: FeatureId
    edges_count: int
    edges: tuple[dict[str, str], ...] = field(default_factory=tuple)


class RegisterCodeTraceabilityUseCase:
    """Caso de uso para registrar aristas de trazabilidad entre características, requisitos y código."""

    def __init__(
        self,
        traceability_repo: TraceabilityRepository,
        requirement_repo: RequirementRepository | None = None,
    ) -> None:
        self._traceability_repo = traceability_repo
        self._requirement_repo = requirement_repo

    async def execute(
        self,
        input_data: RegisterCodeTraceabilityInput,
    ) -> RegisterCodeTraceabilityOutput:
        # 1. Si clean_previous es True, eliminar aristas previas asociadas a la entidad y sus requisitos
        if input_data.clean_previous:
            await self._traceability_repo.delete_by_entity_id(str(input_data.feature_id))
            if input_data.mappings:
                for mapping in input_data.mappings:
                    req_key = format_requirement_key(input_data.feature_id, mapping.requirement_code)
                    await self._traceability_repo.delete_by_entity_id(req_key)
            elif self._requirement_repo is not None:
                markdown = await self._requirement_repo.by_feature_id(input_data.feature_id)
                if markdown:
                    for match in _REQ_CODE_RE.finditer(markdown):
                        req_key = format_requirement_key(input_data.feature_id, match.group(0).upper())
                        await self._traceability_repo.delete_by_entity_id(req_key)

        edges: list[dict[str, str]] = []

        async def _add_edge(
            source_type: str,
            source_id: str,
            target_type: str,
            target_id: str,
        ) -> None:
            await self._traceability_repo.add_edge(
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                origin=input_data.origin,
            )
            edges.append(
                {
                    "source_type": source_type,
                    "source_id": source_id,
                    "target_type": target_type,
                    "target_id": target_id,
                    "origin": input_data.origin,
                }
            )

        # 2. Registrar aristas Feature -> Archivos Generados
        for file_path in input_data.generated_files:
            target_type = "test_file" if _is_test_file(file_path) else "code_file"
            await _add_edge(
                source_type="feature",
                source_id=str(input_data.feature_id),
                target_type=target_type,
                target_id=file_path,
            )

        # 3. Determinar los mapeos de requisitos a archivos
        effective_mappings: list[RequirementCodeMapping] = list(input_data.mappings)

        if not effective_mappings and self._requirement_repo is not None:
            markdown = await self._requirement_repo.by_feature_id(input_data.feature_id)
            if markdown:
                found_codes: list[str] = []
                for match in _REQ_CODE_RE.finditer(markdown):
                    code = match.group(0).upper()
                    if code not in found_codes:
                        found_codes.append(code)

                code_files = tuple(f for f in input_data.generated_files if not _is_test_file(f))
                test_files = tuple(f for f in input_data.generated_files if _is_test_file(f))

                for code in found_codes:
                    effective_mappings.append(
                        RequirementCodeMapping(
                            requirement_code=code,
                            code_files=code_files,
                            test_files=test_files,
                        )
                    )

        # 4. Registrar aristas Requisito -> Archivos de Código y Pruebas
        for mapping in effective_mappings:
            req_key = format_requirement_key(input_data.feature_id, mapping.requirement_code)

            for cf in mapping.code_files:
                await _add_edge(
                    source_type="requirement",
                    source_id=req_key,
                    target_type="code_file",
                    target_id=cf,
                )

            for tf in mapping.test_files:
                await _add_edge(
                    source_type="requirement",
                    source_id=req_key,
                    target_type="test_file",
                    target_id=tf,
                )

        return RegisterCodeTraceabilityOutput(
            feature_id=input_data.feature_id,
            edges_count=len(edges),
            edges=tuple(edges),
        )
