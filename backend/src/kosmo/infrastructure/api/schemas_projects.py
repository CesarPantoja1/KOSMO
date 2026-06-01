"""DTOs Pydantic para operaciones de proyectos."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=256,
        description="Nombre del proyecto.",
        examples=["Sistema de Gestion de Inventario"],
    )
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Descripcion del proyecto, que sera usada para generar el discovery inicial.",
        examples=["Sistema de gestion de inventario en tiempo real para pequenas empresas."],
    )


class ProjectListItem(BaseModel):
    id: str
    name: str
    slug: str = ""
    description: str
    current_phase: str
    status: str
    last_activity_at: datetime


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str = ""
    description: str
    current_phase: str
    status: str
    last_activity_at: datetime
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
