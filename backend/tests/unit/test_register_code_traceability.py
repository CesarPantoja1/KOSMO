from __future__ import annotations

import pytest

from kosmo.application.codegen.register_code_traceability import (
    RegisterCodeTraceabilityInput,
    RegisterCodeTraceabilityUseCase,
    RequirementCodeMapping,
    format_requirement_key,
)
from kosmo.contracts.sdd.ids import FeatureId
from tests.unit.fakes import InMemoryRequirementRepository, InMemoryTraceabilityRepository


@pytest.mark.unit
def test_format_requirement_key_helper() -> None:
    feat_id = FeatureId("feat_01")
    assert format_requirement_key(feat_id, "REQ-1.1") == "feat_01:REQ-1.1"
    assert format_requirement_key("feat_01", "REQ-1.2") == "feat_01:REQ-1.2"
    # Idempotente si ya tiene el prefijo
    assert format_requirement_key("feat_01", "feat_01:REQ-1.1") == "feat_01:REQ-1.1"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_register_code_traceability_feature_to_generated_files() -> None:
    # Arrange
    trace_repo = InMemoryTraceabilityRepository()
    use_case = RegisterCodeTraceabilityUseCase(traceability_repo=trace_repo)
    feat_id = FeatureId("feat_01HT")
    input_data = RegisterCodeTraceabilityInput(
        feature_id=feat_id,
        generated_files=("src/calc.ts", "tests/calc.test.ts"),
    )

    # Act
    output = await use_case.execute(input_data)

    # Assert
    assert output.edges_count == 2
    assert ("feature", "feat_01HT", "code_file", "src/calc.ts", "codegen") in trace_repo.edges
    assert ("feature", "feat_01HT", "test_file", "tests/calc.test.ts", "codegen") in trace_repo.edges


@pytest.mark.asyncio
@pytest.mark.unit
async def test_register_code_traceability_requirement_to_code_and_test_files() -> None:
    # Arrange
    trace_repo = InMemoryTraceabilityRepository()
    use_case = RegisterCodeTraceabilityUseCase(traceability_repo=trace_repo)
    feat_id = FeatureId("feat_02")
    input_data = RegisterCodeTraceabilityInput(
        feature_id=feat_id,
        generated_files=("src/expenses.ts", "tests/expenses.test.ts"),
        mappings=(
            RequirementCodeMapping(
                requirement_code="REQ-2.1",
                code_files=("src/expenses.ts",),
                test_files=("tests/expenses.test.ts",),
            ),
            RequirementCodeMapping(
                requirement_code="REQ-2.2",
                code_files=("src/expenses.ts",),
                test_files=(),
            ),
        ),
    )

    # Act
    output = await use_case.execute(input_data)

    # Assert
    # 2 feature edges + 2 for REQ-2.1 (code + test) + 1 for REQ-2.2 (code) = 5 edges
    assert output.edges_count == 5
    assert ("requirement", "feat_02:REQ-2.1", "code_file", "src/expenses.ts", "codegen") in trace_repo.edges
    assert ("requirement", "feat_02:REQ-2.1", "test_file", "tests/expenses.test.ts", "codegen") in trace_repo.edges
    assert ("requirement", "feat_02:REQ-2.2", "code_file", "src/expenses.ts", "codegen") in trace_repo.edges


@pytest.mark.asyncio
@pytest.mark.unit
async def test_register_code_traceability_preserves_other_features() -> None:
    # Arrange
    trace_repo = InMemoryTraceabilityRepository()
    # Agregar aristas previas de feat_01
    await trace_repo.add_edge("feature", "feat_01", "code_file", "src/login.ts", "codegen")
    await trace_repo.add_edge("requirement", "feat_01:REQ-1.1", "code_file", "src/login.ts", "codegen")

    use_case = RegisterCodeTraceabilityUseCase(traceability_repo=trace_repo)
    feat_id_2 = FeatureId("feat_02")
    input_data = RegisterCodeTraceabilityInput(
        feature_id=feat_id_2,
        generated_files=("src/profile.ts",),
        mappings=(
            RequirementCodeMapping(
                requirement_code="REQ-2.1",
                code_files=("src/profile.ts",),
            ),
        ),
    )

    # Act
    await use_case.execute(input_data)

    # Assert
    # Las aristas de feat_01 siguen intactas
    assert ("feature", "feat_01", "code_file", "src/login.ts", "codegen") in trace_repo.edges
    assert ("requirement", "feat_01:REQ-1.1", "code_file", "src/login.ts", "codegen") in trace_repo.edges
    # Las de feat_02 se agregaron
    assert ("feature", "feat_02", "code_file", "src/profile.ts", "codegen") in trace_repo.edges
    assert ("requirement", "feat_02:REQ-2.1", "code_file", "src/profile.ts", "codegen") in trace_repo.edges


@pytest.mark.asyncio
@pytest.mark.unit
async def test_register_code_traceability_cleans_previous_feature_edges() -> None:
    # Arrange
    trace_repo = InMemoryTraceabilityRepository()
    feat_id = FeatureId("feat_03")

    # Registro inicial de feat_03
    await trace_repo.add_edge("feature", "feat_03", "code_file", "src/old.ts", "codegen")
    await trace_repo.add_edge("requirement", "feat_03:REQ-3.1", "code_file", "src/old.ts", "codegen")

    use_case = RegisterCodeTraceabilityUseCase(traceability_repo=trace_repo)
    input_data = RegisterCodeTraceabilityInput(
        feature_id=feat_id,
        generated_files=("src/new.ts",),
        mappings=(
            RequirementCodeMapping(
                requirement_code="REQ-3.1",
                code_files=("src/new.ts",),
            ),
        ),
        clean_previous=True,
    )

    # Act
    await use_case.execute(input_data)

    # Assert
    # Las aristas antiguas de feat_03 fueron reemplazadas
    assert ("feature", "feat_03", "code_file", "src/old.ts", "codegen") not in trace_repo.edges
    assert ("requirement", "feat_03:REQ-3.1", "code_file", "src/old.ts", "codegen") not in trace_repo.edges
    # Las nuevas están presentes
    assert ("feature", "feat_03", "code_file", "src/new.ts", "codegen") in trace_repo.edges
    assert ("requirement", "feat_03:REQ-3.1", "code_file", "src/new.ts", "codegen") in trace_repo.edges


@pytest.mark.asyncio
@pytest.mark.unit
async def test_register_code_traceability_infers_from_requirement_repo_when_mappings_omitted() -> None:
    # Arrange
    trace_repo = InMemoryTraceabilityRepository()
    req_repo = InMemoryRequirementRepository()
    feat_id = FeatureId("feat_04")

    # Guardar markdown con 2 requisitos
    markdown = "### REQ-4.1 Registro\nUbicuo...\n### REQ-4.2 Edicion\nBasado en eventos..."
    await req_repo.save(feat_id, markdown)

    use_case = RegisterCodeTraceabilityUseCase(
        traceability_repo=trace_repo,
        requirement_repo=req_repo,
    )
    input_data = RegisterCodeTraceabilityInput(
        feature_id=feat_id,
        generated_files=("src/users.ts", "tests/users.test.ts"),
    )

    # Act
    output = await use_case.execute(input_data)

    # Assert
    assert output.edges_count >= 4
    assert ("requirement", "feat_04:REQ-4.1", "code_file", "src/users.ts", "codegen") in trace_repo.edges
    assert ("requirement", "feat_04:REQ-4.1", "test_file", "tests/users.test.ts", "codegen") in trace_repo.edges
    assert ("requirement", "feat_04:REQ-4.2", "code_file", "src/users.ts", "codegen") in trace_repo.edges
    assert ("requirement", "feat_04:REQ-4.2", "test_file", "tests/users.test.ts", "codegen") in trace_repo.edges
