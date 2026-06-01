from kosmo.contracts.sdd.domain_model import (
    BoundaryDefinition,
    DomainModel,
    UMLClass,
    UMLRelationship,
)
from kosmo.domain.sdd.validators.domain_model_validator import validate_domain_model


class TestDomainModelValidator:
    def test_empty_model_passes(self) -> None:
        model = DomainModel()
        findings = validate_domain_model(model)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0

    def test_duplicate_class_ids_detected(self) -> None:
        model = DomainModel(
            classes=[
                UMLClass(id="cls-1", name="A"),
                UMLClass(id="cls-1", name="B"),
            ]
        )
        findings = validate_domain_model(model)
        errors = [f for f in findings if f.severity == "error"]
        assert any("duplicados" in e.message.lower() for e in errors)

    def test_orphan_relationship_detected(self) -> None:
        model = DomainModel(
            relationships=[
                UMLRelationship(
                    id="rel-1",
                    source_class_id="nonexistent",
                    target_class_id="cls-1",
                    relationship_type="association",
                )
            ],
            classes=[UMLClass(id="cls-1", name="A")],
        )
        findings = validate_domain_model(model)
        errors = [f for f in findings if f.severity == "error"]
        assert any("no existe" in e.message.lower() for e in errors)

    def test_missing_cardinality_warns(self) -> None:
        model = DomainModel(
            classes=[
                UMLClass(id="cls-1", name="A"),
                UMLClass(id="cls-2", name="B"),
            ],
            relationships=[
                UMLRelationship(
                    id="rel-1",
                    source_class_id="cls-1",
                    target_class_id="cls-2",
                    relationship_type="association",
                )
            ],
        )
        findings = validate_domain_model(model)
        warnings = [f for f in findings if f.severity == "warning"]
        assert any("cardinalidad" in w.message.lower() for w in warnings)

    def test_duplicate_boundary_names_detected(self) -> None:
        model = DomainModel(
            boundaries=[
                BoundaryDefinition(name="b1", owned_modules=["m1"]),  # type: ignore[arg-type]
                BoundaryDefinition(name="b1", owned_modules=["m2"]),  # type: ignore[arg-type]
            ]
        )
        findings = validate_domain_model(model)
        errors = [f for f in findings if f.severity == "error"]
        assert any("duplicados" in e.message.lower() for e in errors)

    def test_valid_model_passes(self) -> None:
        model = DomainModel(
            classes=[
                UMLClass(id="cls-1", name="A"),
                UMLClass(id="cls-2", name="B"),
            ],
            relationships=[
                UMLRelationship(
                    id="rel-1",
                    source_class_id="cls-1",
                    target_class_id="cls-2",
                    relationship_type="association",
                    source_cardinality="1",
                    target_cardinality="*",
                )
            ],
        )
        findings = validate_domain_model(model)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0
