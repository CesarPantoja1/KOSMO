from pydantic import BaseModel


class CustomConstitution(BaseModel):
    api_standards: str | None = None
    authentication: str | None = None
    database: str | None = None
    deployment: str | None = None
    error_handling: str | None = None
    security: str | None = None
    testing: str | None = None


class Constitution(BaseModel):
    product: str
    tech: str
    structure: str
    custom: CustomConstitution | None = None


class FrozenConstitution(Constitution):
    version_hash: str
