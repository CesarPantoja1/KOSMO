from kosmo.contracts.sdd.discovery import DiscoveryDocument, RawIdea


class TestDiscoveryModel:
    def test_raw_idea_defaults(self) -> None:
        idea = RawIdea(text="test")
        assert idea.assumptions == []
        assert idea.constraints == []
        assert idea.optional_context == ""

    def test_discovery_document(self) -> None:
        discovery = DiscoveryDocument(
            vision="Test vision",
            problem_space="Test problem",
            scope="Test scope",
        )
        data = discovery.model_dump()
        assert data["vision"] == "Test vision"
        assert data["problem_space"] == "Test problem"
