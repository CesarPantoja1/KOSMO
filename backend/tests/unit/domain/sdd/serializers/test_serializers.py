from kosmo.contracts.sdd.domain_model import DomainModel, UMLAttribute, UMLClass
from kosmo.domain.sdd.serializers.plantuml_serializer import to_plantuml
from kosmo.domain.sdd.serializers.xmi_serializer import to_xmi


class TestPlantUMLSerializer:
    def test_empty_model(self) -> None:
        result = to_plantuml(DomainModel())
        assert "@startuml" in result
        assert "@enduml" in result

    def test_model_with_class(self) -> None:
        model = DomainModel(
            classes=[
                UMLClass(
                    id="cls-1",
                    name="UserService",
                    attributes=[UMLAttribute(name="db", type="Database")],
                )
            ]
        )
        result = to_plantuml(model)
        assert "class UserService" in result
        assert "db: Database" in result

    def test_model_with_abstract_class(self) -> None:
        model = DomainModel(classes=[UMLClass(id="cls-1", name="BaseRepo", is_abstract=True)])
        result = to_plantuml(model)
        assert "abstract class BaseRepo" in result


class TestXMISerializer:
    def test_empty_model(self) -> None:
        result = to_xmi(DomainModel())
        assert "<xmi:XMI" in result
        assert "uml:Model" in result

    def test_model_with_class(self) -> None:
        model = DomainModel(classes=[UMLClass(id="cls-1", name="User")])
        result = to_xmi(model)
        assert 'name="User"' in result
        assert 'xmi:type="uml:Class"' in result

    def test_xmi_contains_namespace(self) -> None:
        result = to_xmi(DomainModel())
        assert "xmlns:xmi=" in result
        assert "xmlns:uml=" in result
