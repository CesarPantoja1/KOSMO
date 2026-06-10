from kosmo.contracts.sdd.ears import AcceptanceCriterion, EARSPattern, EARSRequirement
from kosmo.contracts.sdd.ids import RequirementId
from kosmo.domain.sdd.validators.ears_validator import (
    ValidationSeverity,
    detect_ambiguity,
    detect_ears_pattern,
    detect_implementation_leak,
    is_measurable,
    score_requirement,
    score_requirements_batch,
    validate_requirement,
)


class TestEARSValidator:
    def test_valid_ubiquitous_passes(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-1"),
            pattern=EARSPattern.UBIQUITOUS,
            system="El sistema",
            response="identifica de forma unica cada pedido",
            source_statement="The system shall identificar de forma unica cada pedido.",
            acceptance_criteria=[
                AcceptanceCriterion(
                    description="Cada pedido recibe un identificador unico",
                    scenario="Dado que se crea un pedido, cuando el sistema lo registra, entonces asigna un identificador",
                    expected_result="El pedido tiene un ID que no se repite",
                )
            ],
            rationale="Trazabilidad de pedidos requerida por el negocio",
        )
        findings = validate_requirement(req)
        errors = [f for f in findings if f.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_valid_event_passes(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-2"),
            pattern=EARSPattern.EVENT,
            trigger="WHEN el cliente confirma el pedido",
            system="El sistema",
            response="reserva el inventario",
            source_statement="WHEN el cliente confirma el pedido, the system shall reservar el inventario.",
            acceptance_criteria=[
                AcceptanceCriterion(description="Inventario reservado tras confirmacion")
            ],
        )
        findings = validate_requirement(req)
        errors = [f for f in findings if f.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_missing_acceptance_criteria_warns(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-3"),
            pattern=EARSPattern.UBIQUITOUS,
            system="El sistema",
            response="validara credenciales",
            source_statement="The system shall validar credenciales.",
        )
        findings = validate_requirement(req)
        warnings = [f for f in findings if f.severity == ValidationSeverity.WARNING]
        assert any(
            "aceptación" in f.message.lower() or "aceptacion" in f.message.lower() for f in warnings
        )

    def test_empty_source_rejected(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-4"),
            pattern=EARSPattern.UBIQUITOUS,
            system="El sistema",
            response="respuesta",
            source_statement="",
        )
        findings = validate_requirement(req)
        errors = [f for f in findings if f.severity == ValidationSeverity.ERROR]
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


class TestImplementationLeakDetection:
    def test_detect_api_leak(self) -> None:
        leaks = detect_implementation_leak("WHEN the endpoint POST /orders recibe datos")
        assert len(leaks) > 0
        assert any("API" in leak.category for leak in leaks)

    def test_detect_database_leak(self) -> None:
        leaks = detect_implementation_leak("The system shall guardar en la base de datos")
        assert len(leaks) > 0
        assert any("base de datos" in leak.category for leak in leaks)

    def test_detect_framework_leak(self) -> None:
        leaks = detect_implementation_leak("El componente React mostrara los productos")
        assert len(leaks) > 0
        assert any("react" in leak.matched_text.lower() for leak in leaks)

    def test_detect_language_leak(self) -> None:
        leaks = detect_implementation_leak("The Python backend procesara la solicitud")
        assert len(leaks) > 0
        assert any("python" in leak.matched_text.lower() for leak in leaks)

    def test_clean_business_statement_passes(self) -> None:
        leaks = detect_implementation_leak(
            "WHEN el cliente confirma el pedido, the system shall notificar al cliente"
        )
        assert len(leaks) == 0

    def test_multiple_leaks_detected(self) -> None:
        leaks = detect_implementation_leak("La API REST en Node.js guardara en MongoDB el registro")
        assert len(leaks) >= 3

    def test_blocker_finding_on_leak(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-leak"),
            pattern=EARSPattern.UBIQUITOUS,
            system="El sistema",
            response="responder",
            source_statement="The system shall guardar en la base de datos PostgreSQL.",
        )
        findings = validate_requirement(req)
        blockers = [f for f in findings if f.severity == ValidationSeverity.BLOCKER]
        assert len(blockers) > 0
        assert any("fuga" in b.message.lower() for b in blockers)


class TestAmbiguityDetection:
    def test_detect_vague_fast(self) -> None:
        ambs = detect_ambiguity("El sistema debe ser rapido en todas las operaciones")
        assert any("rápido" in a for a in ambs)

    def test_detect_vague_secure(self) -> None:
        ambs = detect_ambiguity("El sistema debe ser seguro en todo momento")
        assert any("seguro" in a for a in ambs)

    def test_detect_vague_robust(self) -> None:
        ambs = detect_ambiguity("El sistema debe ser robusto ante fallos")
        assert any("robusto" in a for a in ambs)

    def test_clean_statement_no_ambiguity(self) -> None:
        ambs = detect_ambiguity(
            "WHEN el cliente confirma el pedido, the system shall reservar el inventario en menos de 5 segundos"
        )
        assert len(ambs) == 0


class TestMeasurability:
    def test_measurable_criterion_with_time(self) -> None:
        ac = AcceptanceCriterion(
            description="El sistema responde en menos de 3 segundos",
            expected_result="Tiempo de respuesta inferior a 3 segundos",
        )
        assert is_measurable(ac) is True

    def test_measurable_criterion_with_percentage(self) -> None:
        ac = AcceptanceCriterion(
            description="El sistema procesa al menos el 95% de las solicitudes",
        )
        assert is_measurable(ac) is True

    def test_measurable_criterion_with_notify(self) -> None:
        ac = AcceptanceCriterion(
            description="El sistema notifica al cliente",
        )
        assert is_measurable(ac) is True

    def test_non_measurable_criterion(self) -> None:
        ac = AcceptanceCriterion(
            description="El sistema debe ser bueno",
        )
        assert is_measurable(ac) is False

    def test_measurable_with_scenario(self) -> None:
        ac = AcceptanceCriterion(
            description="Notificacion enviada",
            scenario="Dado que el pedido esta listo, cuando han pasado menos de 5 minutos, entonces se notifica al cliente",
        )
        assert is_measurable(ac) is True


class TestRequirementScoring:
    def test_clean_business_requirement_scores_high(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-score"),
            pattern=EARSPattern.EVENT,
            trigger="WHEN el cliente confirma el pedido",
            system="El sistema",
            response="reserva el inventario y notifica al cliente",
            source_statement="WHEN el cliente confirma el pedido, the system shall reservar el inventario y notificar al cliente.",
            acceptance_criteria=[
                AcceptanceCriterion(
                    description="Inventario reservado al confirmar",
                    scenario="Dado que hay stock disponible, cuando el cliente confirma, entonces el inventario se reduce",
                    expected_result="El stock se actualiza y el cliente recibe confirmacion",
                ),
                AcceptanceCriterion(
                    description="Cliente notificado en menos de 30 segundos",
                    scenario="Dado que el pedido se confirma, cuando pasan menos de 30 segundos, entonces el cliente recibe notificacion",
                    expected_result="Notificacion entregada en menos de 30 segundos",
                ),
            ],
            rationale="Evitar sobreventa y mantener informado al cliente",
        )
        card = score_requirement(req)
        assert card.overall_score >= 7.0
        assert card.passed is True
        assert len(card.blocker_findings) == 0

    def test_leaky_requirement_scores_low(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-bad"),
            pattern=EARSPattern.UBIQUITOUS,
            system="El sistema",
            response="guardar datos",
            source_statement="The system shall guardar el registro en la tabla customers de PostgreSQL.",
            acceptance_criteria=[AcceptanceCriterion(description="Dato guardado")],
        )
        card = score_requirement(req)
        assert card.passed is False
        pureza = next((d for d in card.dimensions if d.name == "pureza_negocio"), None)
        assert pureza is not None
        assert pureza.score == 0.0

    def test_batch_scoring_detects_gaps(self) -> None:
        reqs = [
            EARSRequirement(
                id=RequirementId("R-b1"),
                pattern=EARSPattern.UBIQUITOUS,
                system="El sistema",
                response="identificar pedidos",
                source_statement="The system shall identificar cada pedido de forma unica.",
                acceptance_criteria=[AcceptanceCriterion(description="ID unico")],
            ),
        ]
        batch = score_requirements_batch(reqs)
        assert batch.total_requirements == 1
        assert any("Eventos" in f or "Estados" in f for f in batch.summary_findings)

    def test_batch_detects_duplicates(self) -> None:
        reqs = [
            EARSRequirement(
                id=RequirementId("R-dup1"),
                pattern=EARSPattern.EVENT,
                trigger="WHEN user clicks",
                system="El sistema",
                response="notificar",
                source_statement="WHEN user clicks, the system shall notify.",
            ),
            EARSRequirement(
                id=RequirementId("R-dup2"),
                pattern=EARSPattern.EVENT,
                trigger="WHEN user clicks",
                system="El sistema",
                response="notificar",
                source_statement="WHEN user clicks, the system shall notify.",
            ),
        ]
        batch = score_requirements_batch(reqs)
        assert any("duplicado" in f.lower() for f in batch.summary_findings)
