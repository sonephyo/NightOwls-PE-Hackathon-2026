"""
Unit tests for pure utility functions.

These tests do not require a running database or Flask application context;
each function is exercised in complete isolation via mocking where needed.
"""

import json
import string
from unittest.mock import MagicMock, patch

import pytest

from app.routes.urls import generate_short_code
from app.routes.events import event_to_dict


# ---------------------------------------------------------------------------
# generate_short_code
# ---------------------------------------------------------------------------

class TestGenerateShortCode:
    VALID_CHARS = set(string.ascii_letters + string.digits)

    def test_default_length(self):
        code = generate_short_code()
        assert len(code) == 6

    def test_custom_length(self):
        for length in (1, 4, 10, 20):
            assert len(generate_short_code(length)) == length

    def test_only_alphanumeric_characters(self):
        for _ in range(50):
            code = generate_short_code(12)
            assert set(code).issubset(self.VALID_CHARS), (
                f"Non-alphanumeric character found in {code!r}"
            )

    def test_returns_string(self):
        assert isinstance(generate_short_code(), str)

    def test_randomness_produces_different_values(self):
        """Generate 100 codes; they should not all be identical."""
        codes = {generate_short_code() for _ in range(100)}
        assert len(codes) > 1


# ---------------------------------------------------------------------------
# event_to_dict
# ---------------------------------------------------------------------------

class TestEventToDict:
    """Tests for event_to_dict, with model_to_dict mocked out."""

    def _call(self, raw_dict):
        """Patch model_to_dict to return *raw_dict*, then call event_to_dict."""
        mock_event = MagicMock()
        with patch("app.routes.events.model_to_dict", return_value=raw_dict):
            return event_to_dict(mock_event)

    def test_parses_valid_json_details(self):
        payload = {"browser": "firefox", "os": "linux"}
        result = self._call({"id": 1, "details": json.dumps(payload)})
        assert result["details"] == payload

    def test_passes_through_none_details(self):
        result = self._call({"id": 1, "details": None})
        assert result["details"] is None

    def test_passes_through_already_dict_details(self):
        """If details is already a dict (not a string), it is left unchanged."""
        d = {"key": "value"}
        result = self._call({"id": 1, "details": d})
        assert result["details"] == d

    def test_passes_through_invalid_json_string(self):
        """Invalid JSON should be left as-is, not raise an exception."""
        bad_json = "not valid json {{{"
        result = self._call({"id": 1, "details": bad_json})
        assert result["details"] == bad_json

    def test_preserves_other_fields(self):
        raw = {"id": 42, "event_type": "click", "details": None}
        result = self._call(raw)
        assert result["id"] == 42
        assert result["event_type"] == "click"

    def test_returns_dict(self):
        result = self._call({"id": 1, "details": None})
        assert isinstance(result, dict)
