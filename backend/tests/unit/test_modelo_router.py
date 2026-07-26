from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from kosmo.application.modelo import (
    GenerateDiagramOutput,
    GetDiagramOutput,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ModeloPhaseOutput,
    ValidationResult,
)
from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.errors import (
    DiagramNotFoundError,
    FeatureNotFoundError,
    LLMInvocationError,
)
from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId
from kosmo.infrastructure.api.routers.modelo import (
    GenerateDiagramRequest,
    generate_diagram,
    get_diagram,
)


def _principal() -> Principal:
    return Principal(subject="usr_test123", scopes=frozenset({"*"}))


def _make_mock_request(generate_uc: Any = None, get_uc: Any = None) -> MagicMock:
    req = MagicMock()
    req.app.state.generate_diagram = generate_uc
    req.app.state.get_diagram = get_uc
    return req


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_endpoint_success() -> None:
    now = datetime.now(UTC)
    diagram = DiagramaActividad(
        id=ActivityDiagramId("diag_01"),
        feature_id=FeatureId("feat_01"),
        diagram_syntax="@startuml\nstart\nstop\n@enduml",
        created_at=now,
        updated_at=now,
    )
    phase_output = ModeloPhaseOutput(
        feature_id=FeatureId("feat_01"),
        diagram_syntax="@startuml\nstart\nstop\n@enduml",
        validation_result=ValidationResult(is_valid=True),
        generation_metadata=GenerationMetadata(),
    )

    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(
        return_value=GenerateDiagramOutput(
            diagram=diagram,
            phase_output=phase_output,
        )
    )

    req = _make_mock_request(generate_uc=mock_uc)
    body = GenerateDiagramRequest(project_id="prj_01")

    res = await generate_diagram("feat_01", body, _principal(), req)

    assert res["id"] == "diag_01"
    assert res["feature_id"] == "feat_01"
    assert "@startuml" in res["diagram_syntax"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_endpoint_feature_not_found() -> None:
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(side_effect=FeatureNotFoundError(feature_id="feat_missing"))

    req = _make_mock_request(generate_uc=mock_uc)
    body = GenerateDiagramRequest(project_id="prj_01")

    with pytest.raises(HTTPException) as exc_info:
        await generate_diagram("feat_missing", body, _principal(), req)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_diagram_endpoint_llm_error() -> None:
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(side_effect=LLMInvocationError(detail="LLM failed"))

    req = _make_mock_request(generate_uc=mock_uc)
    body = GenerateDiagramRequest(project_id="prj_01")

    with pytest.raises(HTTPException) as exc_info:
        await generate_diagram("feat_01", body, _principal(), req)

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_endpoint_success() -> None:
    now = datetime.now(UTC)
    diagram = DiagramaActividad(
        id=ActivityDiagramId("diag_01"),
        feature_id=FeatureId("feat_01"),
        diagram_syntax="@startuml\nstart\nstop\n@enduml",
        created_at=now,
        updated_at=now,
    )

    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(return_value=GetDiagramOutput(diagram=diagram))

    req = _make_mock_request(get_uc=mock_uc)

    res = await get_diagram("feat_01", _principal(), req, project_id="prj_01")

    assert res["id"] == "diag_01"
    assert res["feature_id"] == "feat_01"
    assert res["diagram_syntax"] == "@startuml\nstart\nstop\n@enduml"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_diagram_endpoint_not_found() -> None:
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(side_effect=DiagramNotFoundError(feature_id="feat_01"))

    req = _make_mock_request(get_uc=mock_uc)

    with pytest.raises(HTTPException) as exc_info:
        await get_diagram("feat_01", _principal(), req, project_id="prj_01")

    assert exc_info.value.status_code == 404
