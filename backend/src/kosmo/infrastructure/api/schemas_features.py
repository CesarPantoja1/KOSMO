"""DTOs Pydantic para operaciones de caracteristicas (features)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateFeatureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        max_length=256,
        description="Titulo de la caracteristica.",
        examples=["Gestion de productos"],
    )
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Descripcion de la caracteristica en lenguaje de negocio.",
        examples=["Crear, editar y eliminar productos del catalogo."],
    )


class FeatureResponse(BaseModel):
    id: str
    project_id: str
    title: str
    slug: str = ""
    description: str
    status: str
    created_at: datetime


class FeaturesListResponse(BaseModel):
    features: list[FeatureResponse]
    total: int


class ImproveFeatureResponse(BaseModel):
    id: str
    project_id: str
    title: str
    slug: str = ""
    description: str
    status: str
    created_at: datetime


class ApplyImprovementRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=256,
        description="Titulo de la caracteristica mejorada.",
    )
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Descripcion de la caracteristica mejorada.",
    )


class FeatureAlternativesResponse(BaseModel):
    suggestions: list[FeatureResponse]


class SuggestFromIdeaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idea: str = Field(
        min_length=1,
        max_length=2000,
        description="Idea o descripcion basica de la caracteristica a crear.",
        examples=["Alertas de stock bajo"],
    )
