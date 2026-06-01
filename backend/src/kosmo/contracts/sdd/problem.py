from typing import Any

from pydantic import BaseModel, Field


class Violation(BaseModel):
    loc: list[str] = []
    msg: str
    input: Any | None = None


class ProblemDetail(BaseModel):
    type: str = Field(default="urn:kosmo:internal:unexpected")
    title: str = Field(default="Error inesperado")
    status: int = Field(default=500)
    detail: str = Field(default="Ocurrió un error inesperado en el servidor.")
    instance: str = Field(default="")
    trace_id: str = Field(default="")
    violations: list[Violation] = Field(default_factory=list)
