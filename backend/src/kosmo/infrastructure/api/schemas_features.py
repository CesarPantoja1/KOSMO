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


class SuggestedFeatureResponse(BaseModel):
    title: str = Field(description="Titulo conciso en infinitivo o sustantivo del dominio")
    description: str = Field(description="Descripcion de valor de negocio")
    rationale: str = Field(
        default="",
        description="Por que esta caracteristica es relevante",
    )
    inferred_from: list[str] = Field(
        default_factory=list,
        description="Secciones de discovery que motivan esta sugerencia",
    )
    category: str = Field(
        default="",
        description="Categoria de negocio inferida",
    )


class FeatureAlternativesResponse(BaseModel):
    suggestions: list[FeatureResponse]
    excluded_titles: list[str] = Field(
        default_factory=list,
        description="Titulos de features existentes excluidas",
    )
    domain_inferred: str = Field(
        default="",
        description="Dominio inferido del discovery",
    )


class SuggestFromIdeaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idea: str = Field(
        min_length=1,
        max_length=2000,
        description="Idea o descripcion basica de la caracteristica a crear.",
        examples=["Alertas de stock bajo"],
    )


class ToggleStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        description="Estado destino: 'aprobada' o 'borrador'.",
        pattern="^(aprobada|borrador)$",
        examples=["aprobada"],
    )


class SaveSuggestionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: list[dict] = Field(
        description="Lista de features seleccionadas con title y description.",
        min_length=1,
        max_length=3,
        examples=[
            [
                {
                    "title": "Alertas de stock bajo",
                    "description": "Notificar cuando el inventario baje del minimo.",
                },
            ]
        ],
    )
