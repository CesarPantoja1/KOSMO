from pydantic import BaseModel

from kosmo.contracts.sdd.ears import EARSRequirement


class RequirementsDocument(BaseModel):
    ubiquitous: list[EARSRequirement] = []
    event: list[EARSRequirement] = []
    state: list[EARSRequirement] = []
    optional: list[EARSRequirement] = []
    unwanted: list[EARSRequirement] = []
    complex: list[EARSRequirement] = []

    @property
    def total(self) -> int:
        return (
            len(self.ubiquitous)
            + len(self.event)
            + len(self.state)
            + len(self.optional)
            + len(self.unwanted)
            + len(self.complex)
        )

    @property
    def all_requirements(self) -> list[EARSRequirement]:
        return (
            self.ubiquitous + self.event + self.state + self.optional + self.unwanted + self.complex
        )
