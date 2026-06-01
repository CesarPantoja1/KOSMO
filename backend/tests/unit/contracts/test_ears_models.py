from kosmo.contracts.sdd.discovery import DiscoveryDocument, RawIdea
from kosmo.contracts.sdd.ears import AcceptanceCriterion, EARSPattern, EARSRequirement
from kosmo.contracts.sdd.ids import RequirementId


class TestEARSModels:
    def test_ubiquitous_requirement_validates(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-1"),
            pattern=EARSPattern.UBIQUITOUS,
            system="El sistema",
            response="validara las credenciales del usuario",
            source_statement="El sistema validara las credenciales del usuario.",
        )
        assert req.id == RequirementId("R-1")
        assert req.pattern == EARSPattern.UBIQUITOUS
        assert req.trigger is None

    def test_event_requirement_validates(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-2"),
            pattern=EARSPattern.EVENT,
            trigger="WHEN el usuario envia el formulario",
            system="El sistema",
            response="procesara la solicitud",
            source_statement=(
                "WHEN el usuario envia el formulario, el sistema procesara la solicitud."
            ),
            acceptance_criteria=[
                AcceptanceCriterion(description="El formulario se procesa en < 2s")
            ],
        )
        assert req.pattern == EARSPattern.EVENT
        assert req.trigger is not None
        assert len(req.acceptance_criteria) == 1

    def test_all_patterns_available(self) -> None:
        patterns = list(EARSPattern)
        assert EARSPattern.UBIQUITOUS in patterns
        assert EARSPattern.EVENT in patterns
        assert EARSPattern.STATE in patterns
        assert EARSPattern.OPTIONAL in patterns
        assert EARSPattern.UNWANTED in patterns
        assert EARSPattern.COMPLEX in patterns


class TestDiscoveryModels:
    def test_raw_idea_minimal(self) -> None:
        idea = RawIdea(text="Una API de gestion de tareas")
        assert idea.text == "Una API de gestion de tareas"
        assert idea.assumptions == []
        assert idea.constraints == []

    def test_raw_idea_with_all_fields(self) -> None:
        idea = RawIdea(
            text="Sistema de inventario",
            assumptions=["Los productos tienen codigo unico"],
            constraints=["Debe usar PostgreSQL"],
        )
        assert len(idea.assumptions) == 1
        assert len(idea.constraints) == 1

    def test_discovery_document_all_fields(self) -> None:
        discovery = DiscoveryDocument(
            vision="Sistema de inventario para pequenas empresas",
            problem_space="Necesidad de control de stock en tiempo real",
            actors="Administradores de inventario",
            value_proposition="Control total del inventario sin software complejo",
            use_cases="Registro de productos, Reportes de stock",
            core_capabilities="Gestion de productos, Alertas de stock bajo",
            business_rules="Solo administradores pueden modificar precios",
            quality_attributes="Alta disponibilidad, interfaz intuitiva",
            scope="Gestion de inventario basico, no incluye integracion ERP",
        )
        assert discovery.vision == "Sistema de inventario para pequenas empresas"
        assert len(discovery.core_capabilities) > 0
        assert len(discovery.scope) > 0
