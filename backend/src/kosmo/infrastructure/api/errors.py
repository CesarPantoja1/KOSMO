from fastapi import Request
from fastapi.responses import JSONResponse

from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    DocumentValidationError,
    FeatureNotApprovedError,
    FeatureNotEditableError,
    FeatureNotFoundError,
    MarkdownParseError,
    ProjectNotFoundError,
    SpecError,
    SpecNotFoundError,
)
from kosmo.contracts.sdd.problem import ProblemDetail

_ERROR_MAP = {
    FeatureNotApprovedError: (409, "urn:kosmo:features:not-approved", "Feature no aprobada"),
    FeatureNotEditableError: (409, "urn:kosmo:features:not-editable", "Feature no editable"),
    FeatureNotFoundError: (404, "urn:kosmo:features:not-found", "Feature no encontrada"),
    DocumentValidationError: (422, "urn:kosmo:document:invalid-structure", "Documento inválido"),
    DocumentNotFoundError: (404, "urn:kosmo:document:not-found", "Documento no encontrado"),
    ProjectNotFoundError: (404, "urn:kosmo:projects:not-found", "Proyecto no encontrado"),
    SpecNotFoundError: (404, "urn:kosmo:specs:not-found", "Especificación no encontrada"),
    MarkdownParseError: (422, "urn:kosmo:document:parse-error", "Error de parseo Markdown"),
}


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "") if hasattr(request.state, "request_id") else ""


async def spec_error_handler(request: Request, exc: SpecError) -> JSONResponse:
    error_type = type(exc)
    if error_type in _ERROR_MAP:
        status, urn, title = _ERROR_MAP[error_type]
    else:
        status, urn, title = 500, "urn:kosmo:internal:unexpected", "Error interno"

    problem = ProblemDetail(
        type=urn,
        title=title,
        status=status,
        detail=str(exc),
        instance=str(request.url.path),
        trace_id=_get_request_id(request),
    )

    return JSONResponse(
        status_code=status,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


async def generic_http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        status = exc.status_code
        detail = str(exc.detail) if exc.detail else "Error de validación"
    else:
        status = 500
        detail = "Error interno del servidor"

    problem = ProblemDetail(
        type="urn:kosmo:internal:unexpected",
        title="Error",
        status=status,
        detail=detail,
        instance=str(request.url.path),
        trace_id=_get_request_id(request),
    )

    return JSONResponse(
        status_code=status,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )
