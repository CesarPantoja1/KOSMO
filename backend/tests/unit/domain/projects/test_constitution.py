from kosmo.contracts.sdd.constitution import Constitution, CustomConstitution
from kosmo.domain.projects.constitution import freeze_constitution


class TestFreezeConstitution:
    def test_freeze_produces_hash(self) -> None:
        c = Constitution(
            product="Test product",
            tech="Python",
            structure="Hexagonal",
        )
        frozen = freeze_constitution(c)
        assert frozen.version_hash is not None
        assert len(frozen.version_hash) == 64

    def test_freeze_is_deterministic(self) -> None:
        c = Constitution(product="X", tech="Y", structure="Z")
        frozen1 = freeze_constitution(c)
        frozen2 = freeze_constitution(c)
        assert frozen1.version_hash == frozen2.version_hash

    def test_freeze_with_custom(self) -> None:
        c = Constitution(
            product="P",
            tech="T",
            structure="S",
            custom=CustomConstitution(
                api_standards="OpenAPI 3.1",
                security="Argon2id",
            ),
        )
        frozen = freeze_constitution(c)
        assert frozen.version_hash is not None
        assert frozen.custom is not None
        assert frozen.custom.api_standards == "OpenAPI 3.1"
