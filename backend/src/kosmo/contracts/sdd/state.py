from pydantic import BaseModel

from kosmo.contracts.sdd.discovery import DiscoveryDocument, ProjectRoadmap, RawIdea
from kosmo.contracts.sdd.domain_model import DomainModel
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.tasks import Task


class SDDState(BaseModel):
    spec_id: str | None = None
    raw_idea: RawIdea | None = None
    discovery: DiscoveryDocument | None = None
    roadmap: ProjectRoadmap | None = None
    features: list[Feature] = []
    requirements: list[EARSRequirement] = []
    design: DomainModel | None = None
    tasks: list[Task] = []
    phase: SpecPhase = SpecPhase.DESCUBRIMIENTO
    errors: list[str] = []
    event_cursor: int = 0
