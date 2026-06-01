from pydantic import BaseModel, Field

from kosmo.contracts.sdd.ids import BoundaryName


class UMLAttribute(BaseModel):
    name: str
    type: str
    visibility: str = "public"
    is_static: bool = False


class UMLOperation(BaseModel):
    name: str
    return_type: str = "void"
    parameters: list[dict[str, str]] = []
    visibility: str = "public"


class UMLClass(BaseModel):
    id: str
    name: str
    attributes: list["UMLAttribute"] = []
    operations: list["UMLOperation"] = []
    is_abstract: bool = False
    stereotype: str | None = None


class UMLRelationship(BaseModel):
    id: str
    source_class_id: str
    target_class_id: str
    relationship_type: str
    source_cardinality: str = ""
    target_cardinality: str = ""
    label: str = ""


class ContractSignature(BaseModel):
    name: str
    methods: list[str] = []
    description: str = ""


class BoundaryDefinition(BaseModel):
    name: BoundaryName
    owned_modules: list[str] = []
    contract: ContractSignature = Field(default_factory=lambda: ContractSignature(name=""))


class DomainModel(BaseModel):
    classes: list["UMLClass"] = []
    relationships: list["UMLRelationship"] = []
    boundaries: list["BoundaryDefinition"] = []
    plantuml: str = ""
    xmi: str = ""
