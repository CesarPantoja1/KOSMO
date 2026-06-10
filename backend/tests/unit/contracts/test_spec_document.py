from kosmo.contracts.sdd.ears import EARSPattern, EARSRequirement
from kosmo.contracts.sdd.ids import ProjectId, RequirementId, SpecId
from kosmo.contracts.sdd.spec import SpecDocument, SpecPhase


class TestSpecDocument:
    def test_spec_document_defaults(self) -> None:
        doc = SpecDocument(
            id=SpecId("spec-1"),
            project_id=ProjectId("proj-1"),
        )
        assert doc.id == SpecId("spec-1")
        assert doc.phase == SpecPhase.DESCUBRIMIENTO
        assert doc.discovery is None
        assert doc.requirements == []
        assert doc.features == []
        assert doc.design is None
        assert doc.tasks == []

    def test_spec_phases(self) -> None:
        assert SpecPhase.DESCUBRIMIENTO == "descubrimiento"
        assert SpecPhase.CARACTERISTICAS == "caracteristicas"
        assert SpecPhase.REQUISITOS == "requisitos"
        assert SpecPhase.MODELO == "modelo"
        assert SpecPhase.IMPLEMENTACION == "implementacion"

    def test_spec_document_with_requirements(self) -> None:
        req = EARSRequirement(
            id=RequirementId("R-1"),
            pattern=EARSPattern.UBIQUITOUS,
            system="Sistema",
            response="hara algo",
            source_statement="El sistema hara algo.",
        )
        doc = SpecDocument(
            id=SpecId("spec-1"),
            project_id=ProjectId("proj-1"),
            requirements=[req],
            phase=SpecPhase.REQUISITOS,
        )
        assert len(doc.requirements) == 1
        assert doc.phase == SpecPhase.REQUISITOS
