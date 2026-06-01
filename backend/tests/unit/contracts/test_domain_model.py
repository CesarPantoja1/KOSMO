from kosmo.contracts.sdd.domain_model import (
    BoundaryDefinition,
    DomainModel,
    UMLAttribute,
    UMLClass,
    UMLOperation,
    UMLRelationship,
)
from kosmo.contracts.sdd.ids import BoundaryName


class TestDomainModel:
    def test_empty_domain_model(self) -> None:
        model = DomainModel()
        assert model.classes == []
        assert model.relationships == []
        assert model.boundaries == []
        assert model.plantuml == ""
        assert model.xmi == ""

    def test_domain_model_with_class(self) -> None:
        cls = UMLClass(
            id="cls-1",
            name="ProductService",
            attributes=[UMLAttribute(name="repository", type="ProductRepository")],
            operations=[UMLOperation(name="find_by_id", return_type="Product")],
        )
        model = DomainModel(classes=[cls])
        assert len(model.classes) == 1
        assert model.classes[0].name == "ProductService"

    def test_domain_model_with_relationships(self) -> None:
        rel = UMLRelationship(
            id="rel-1",
            source_class_id="cls-1",
            target_class_id="cls-2",
            relationship_type="association",
            source_cardinality="1",
            target_cardinality="*",
        )
        model = DomainModel(relationships=[rel])
        assert len(model.relationships) == 1

    def test_boundary_definition(self) -> None:
        boundary = BoundaryDefinition(
            name=BoundaryName("inventory"),
            owned_modules=["inventory.service", "inventory.repository"],
        )
        assert boundary.name == BoundaryName("inventory")
        assert len(boundary.owned_modules) == 2
