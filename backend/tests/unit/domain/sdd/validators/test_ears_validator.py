from kosmo.contracts.sdd.ears import AcceptanceCriterion, EARSPattern, EARSRequirement
from kosmo.contracts.sdd.ids import RequirementId
from kosmo.domain.sdd.validators.ears_validator import (
    detect_ears_pattern,
    validate_requirement,
)


class TestEARSValidator:
    def test_valid_ubiquitous_passes(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-1"),
            pattern=EARSPattern.UBIQUITOUS,
            system="The system",
            response="shall validate credentials",
            source_statement="The system shall validate credentials.",
            acceptance_criteria=[AcceptanceCriterion(description="Test")],
        )
        findings = validate_requirement(req)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0

    def test_valid_event_passes(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-2"),
            pattern=EARSPattern.EVENT,
            trigger="WHEN user logs in",
            system="The system",
            response="shall create a session",
            source_statement="WHEN user logs in, the system shall create a session.",
            acceptance_criteria=[AcceptanceCriterion(description="Session created")],
        )
        findings = validate_requirement(req)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0

    def test_missing_acceptance_criteria_warns(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-3"),
            pattern=EARSPattern.UBIQUITOUS,
            system="S",
            response="R",
            source_statement="S shall R.",
        )
        findings = validate_requirement(req)
        warnings = [f for f in findings if f.severity == "warning"]
        assert any("aceptación" in f.message.lower() for f in warnings)

    def test_empty_source_rejected(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-4"),
            pattern=EARSPattern.UBIQUITOUS,
            system="S",
            response="R",
            source_statement="",
        )
        findings = validate_requirement(req)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) > 0

    def test_detect_event_pattern(self) -> None:
        pattern = detect_ears_pattern("WHEN the user clicks, the system shall respond.")
        assert pattern == EARSPattern.EVENT

    def test_detect_ubiquitous_pattern(self) -> None:
        pattern = detect_ears_pattern("The system shall process the request.")
        assert pattern == EARSPattern.UBIQUITOUS

    def test_detect_state_pattern(self) -> None:
        pattern = detect_ears_pattern("WHILE the session is active, the system shall refresh.")
        assert pattern == EARSPattern.STATE

    def test_detect_unwanted_pattern(self) -> None:
        pattern = detect_ears_pattern("IF the payment fails, THEN the system shall notify.")
        assert pattern == EARSPattern.UNWANTED

    def test_detect_optional_pattern(self) -> None:
        pattern = detect_ears_pattern(
            "WHERE notifications are enabled, the system shall send alerts."
        )
        assert pattern == EARSPattern.OPTIONAL

    def test_missing_pattern_returns_none(self) -> None:
        pattern = detect_ears_pattern("El usuario puede hacer login.")
        assert pattern is None
