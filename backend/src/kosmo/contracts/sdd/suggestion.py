from pydantic import BaseModel, Field


class SuggestedFeature(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=200,
        description="Titulo conciso en infinitivo o sustantivo especifico del dominio",
    )
    description: str = Field(
        min_length=20,
        max_length=600,
        description="Valor de negocio: QUE, PARA QUIEN, BAJO QUE condicion, QUE aporta",
    )
    rationale: str = Field(
        min_length=10,
        max_length=300,
        description="Por que esta caracteristica es relevante para el dominio",
    )
    inferred_from: list[str] = Field(
        default_factory=list,
        description="Secciones de discovery que motivan esta sugerencia",
    )
    category: str = Field(
        default="",
        description="Categoria de negocio: gestion, comunicacion, analitica, etc.",
    )


class SuggestionBatch(BaseModel):
    suggestions: list[SuggestedFeature] = Field(
        min_length=3,
        max_length=3,
        description="Exactamente 3 sugerencias de caracteristicas",
    )
    excluded_titles: list[str] = Field(
        default_factory=list,
        description="Titulos de features existentes que fueron excluidas",
    )
    domain_inferred: str = Field(
        default="",
        description="Dominio inferido del documento de discovery",
    )


class SuggestionResponse(BaseModel):
    suggestions: list[SuggestedFeature]
    excluded_titles: list[str]
    domain_inferred: str
