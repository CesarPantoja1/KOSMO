from kosmo.contracts.sdd.ears import EARSPattern, EARSRequirement
from kosmo.contracts.sdd.ids import RequirementId
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import SDDState


class TestSDDState:
    def test_initial_state(self) -> None:
        state = SDDState()
        assert state.phase == SpecPhase.DESCUBRIMIENTO
        assert state.requirements == []
        assert state.features == []
        assert state.tasks == []
        assert state.errors == []

    def test_state_serialization(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-1"),
            pattern=EARSPattern.UBIQUITOUS,
            system="S",
            response="R",
            source_statement="S shall R",
        )
        state = SDDState(
            spec_id="spec-1",
            requirements=[req],
            phase=SpecPhase.REQUISITOS,
        )
        data = state.model_dump()
        assert data["spec_id"] == "spec-1"
        assert len(data["requirements"]) == 1
