from kosmo.contracts.sdd.ears import EARSPattern, EARSRequirement
from kosmo.contracts.sdd.ids import RequirementId
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import SDDState


class TestSDDState:
    def test_initial_state(self) -> None:
        state = SDDState(project_id="prj_01KT07HCKMM", user_id="usr_01KT07HCKMM")
        assert state.phase == SpecPhase.DESCUBRIMIENTO
        assert state.requirements == []
        assert state.features == []
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
            project_id="prj_01KT07HCKMM",
            user_id="usr_01KT07HCKMM",
            requirements=[req],
            phase=SpecPhase.REQUISITOS,
        )
        data = state.model_dump()
        assert data["project_id"] == "prj_01KT07HCKMM"
        assert len(data["requirements"]) == 1
