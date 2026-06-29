import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


def _make_schema():
    from pydantic import BaseModel

    class MySchema(BaseModel):
        name: str
        score: int

    return MySchema


def _mock_response(text: str):
    resp = MagicMock()
    resp.text = text
    return resp


def _make_mock_genai(response_text: str):
    """Return a mock that replaces the _genai() helper's return value."""
    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value.generate_content.return_value = (
        _mock_response(response_text)
    )
    mock_genai.configure = MagicMock()
    return mock_genai


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="pydantic not installed")
class TestGenerateStructured:
    def test_valid_json_passes_validation(self):
        from core.gemini_client import generate_structured

        schema = _make_schema()
        with patch("core.gemini_client._genai", return_value=_make_mock_genai('{"name": "Alice", "score": 42}')):
            result = generate_structured("test prompt", schema, api_key="fake-key")
        assert result.name == "Alice"
        assert result.score == 42

    def test_json_fence_stripping(self):
        from core.gemini_client import generate_structured

        schema = _make_schema()
        fenced = "```json\n{\"name\": \"Bob\", \"score\": 10}\n```"
        with patch("core.gemini_client._genai", return_value=_make_mock_genai(fenced)):
            result = generate_structured("test prompt", schema, api_key="fake-key")
        assert result.name == "Bob"

    def test_invalid_json_retries_and_raises(self):
        from core.gemini_client import generate_structured

        schema = _make_schema()
        with patch("core.gemini_client._genai", return_value=_make_mock_genai("not valid json")):
            with pytest.raises(ValueError, match="did not return valid JSON"):
                generate_structured("test prompt", schema, api_key="fake-key", max_retries=2)

    def test_validation_error_retries(self):
        from core.gemini_client import generate_structured

        schema = _make_schema()
        # Returns JSON but missing required field 'score'
        with patch("core.gemini_client._genai", return_value=_make_mock_genai('{"name": "Carol"}')):
            with pytest.raises(ValueError):
                generate_structured("test prompt", schema, api_key="fake-key", max_retries=2)
