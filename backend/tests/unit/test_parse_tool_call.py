import pytest

from kosmo.application.pipeline.tool_resolver import _parse_tool_call


@pytest.mark.unit
class TestParseToolCall:
    def test_extracts_tool_name_and_json_args(self) -> None:
        # Arrange
        text = '[TOOL: get_phase_document] {"project_id": "prj_01"}'

        # Act
        name, args = _parse_tool_call(text)

        # Assert
        assert name == "get_phase_document"
        assert args == {"project_id": "prj_01"}

    def test_returns_none_when_no_tool_marker(self) -> None:
        # Arrange
        text = "This is a normal response without any tool call"

        # Act
        name, args = _parse_tool_call(text)

        # Assert
        assert name is None
        assert args == {}

    def test_extracts_name_without_args(self) -> None:
        # Arrange
        text = "[TOOL: get_document]"

        # Act
        name, args = _parse_tool_call(text)

        # Assert
        assert name == "get_document"
        assert args == {}

    def test_returns_empty_args_on_invalid_json(self) -> None:
        # Arrange
        text = "[TOOL: search] {this is not valid json}"

        # Act
        name, args = _parse_tool_call(text)

        # Assert
        assert name == "search"
        assert args == {}

    def test_embedded_brackets_truncate_name_at_first_closing_bracket(self) -> None:
        # Arrange — known limitation: embedded `]` breaks the parser
        text = "[TOOL: find [nested] item]"

        # Act
        name, _ = _parse_tool_call(text)

        # Assert — stops at first `]`, name is truncated
        assert name == "find [nested"

    def test_extracts_first_tool_when_multiple_present(self) -> None:
        # Arrange
        text = '[TOOL: first_tool] {"key": 1} [TOOL: second_tool] {"key": 2}'

        # Act
        name, args = _parse_tool_call(text)

        # Assert
        assert name == "first_tool"
        assert args == {"key": 1}

    def test_strips_whitespace_from_name(self) -> None:
        # Arrange
        text = "[TOOL:   spaced_name   ]"

        # Act
        name, _ = _parse_tool_call(text)

        # Assert
        assert name == "spaced_name"

    def test_nested_json_falls_back_to_empty_args(self) -> None:
        # Arrange — known limitation: parser uses simple {} matching, not balanced
        text = '[TOOL: query] {"filters": {"status": "active", "limit": 10}}'

        # Act
        name, args = _parse_tool_call(text)

        # Assert — inner } terminates the search, outer } is missed, json.loads fails
        assert name == "query"
        assert args == {}

    def test_handles_json_with_arrays(self) -> None:
        # Arrange
        text = '[TOOL: batch] {"ids": ["a", "b", "c"]}'

        # Act
        name, args = _parse_tool_call(text)

        # Assert
        assert name == "batch"
        assert args == {"ids": ["a", "b", "c"]}

    @pytest.mark.parametrize(
        "text,expected_name,expected_args",
        [
            ("[TOOL:simple]", "simple", {}),
            ('[TOOL: x] {"a": 1, "b": "text", "c": true, "d": 3.14}', "x", {"a": 1, "b": "text", "c": True, "d": 3.14}),
            ("[TOOL:empty_json] {}", "empty_json", {}),
            ("[TOOL:ok] {} extra text after", "ok", {}),
            ("prefix text [TOOL: inline] {}", "inline", {}),
        ],
    )
    def test_parametrized_variants(self, text: str, expected_name: str, expected_args: dict) -> None:
        # Arrange is in params

        # Act
        name, args = _parse_tool_call(text)

        # Assert
        assert name == expected_name
        assert args == expected_args
