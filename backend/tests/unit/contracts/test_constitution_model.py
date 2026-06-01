from kosmo.contracts.sdd.constitution import Constitution, CustomConstitution, FrozenConstitution


class TestConstitutionModel:
    def test_constitution_minimal(self) -> None:
        c = Constitution(
            product="Web application",
            tech="Python 3.13, FastAPI, PostgreSQL",
            structure="Hexagonal architecture",
        )
        assert c.product == "Web application"
        assert c.tech == "Python 3.13, FastAPI, PostgreSQL"
        assert c.structure == "Hexagonal architecture"
        assert c.custom is None

    def test_constitution_with_custom(self) -> None:
        custom = CustomConstitution(
            api_standards="RESTful with OpenAPI 3.1",
            database="PostgreSQL with SQLAlchemy async",
        )
        c = Constitution(
            product="API",
            tech="FastAPI",
            structure="Monolith",
            custom=custom,
        )
        assert c.custom is not None
        assert c.custom.api_standards == "RESTful with OpenAPI 3.1"
        assert c.custom.authentication is None

    def test_custom_constitution_all_none_by_default(self) -> None:
        custom = CustomConstitution()
        assert custom.api_standards is None
        assert custom.authentication is None
        assert custom.database is None
        assert custom.deployment is None
        assert custom.error_handling is None
        assert custom.security is None
        assert custom.testing is None

    def test_frozen_constitution(self) -> None:
        c = Constitution(product="x", tech="y", structure="z")
        frozen = FrozenConstitution(**c.model_dump(), version_hash="abc123")
        assert frozen.version_hash == "abc123"
        assert frozen.product == c.product
