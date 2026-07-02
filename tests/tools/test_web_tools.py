"""Unit tests for app/backend/tools/web_tools.py.

requests.get and DDGS are fully mocked.  No real network calls are made.

NOTE: Because tests/tools/conftest.py stubs @tool as a no-op decorator,
the tool functions are plain Python functions here. Called directly.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.backend.tools.web_tools import get_weather, web_search


# ---------------------------------------------------------------------------
# get_weather
# ---------------------------------------------------------------------------
class TestGetWeather:
    def test_returns_weather_text_on_success(self):
        mock_response = MagicMock()
        mock_response.text = "Chennai: ⛅  +30°C"
        with patch("app.backend.tools.web_tools.requests.get", return_value=mock_response):
            result = get_weather("Chennai")
        assert "Chennai" in result
        assert "30" in result

    def test_strips_whitespace_from_response(self):
        mock_response = MagicMock()
        mock_response.text = "   London: 🌧  +15°C   "
        with patch("app.backend.tools.web_tools.requests.get", return_value=mock_response):
            result = get_weather("London")
        assert result == result.strip()

    def test_returns_error_string_on_timeout(self):
        import requests as req
        with patch(
            "app.backend.tools.web_tools.requests.get",
            side_effect=req.exceptions.Timeout("timed out"),
        ):
            result = get_weather("Paris")
        assert "Couldn't fetch weather" in result
        assert "timed out" in result

    def test_returns_error_string_on_connection_error(self):
        import requests as req
        with patch(
            "app.backend.tools.web_tools.requests.get",
            side_effect=req.exceptions.ConnectionError("no internet"),
        ):
            result = get_weather("Tokyo")
        assert "Couldn't fetch weather" in result

    def test_empty_city_string_still_makes_request(self):
        """An empty city string is forwarded to wttr.in; result is whatever the mock returns."""
        mock_response = MagicMock()
        mock_response.text = "No city provided"
        with patch(
            "app.backend.tools.web_tools.requests.get", return_value=mock_response
        ) as mock_get:
            result = get_weather("")
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert "wttr.in/" in call_url

    def test_uses_correct_wttr_format_parameter(self):
        mock_response = MagicMock()
        mock_response.text = "Mumbai: 🌤  +32°C"
        with patch(
            "app.backend.tools.web_tools.requests.get", return_value=mock_response
        ) as mock_get:
            get_weather("Mumbai")
        call_url = mock_get.call_args[0][0]
        assert "?format=3" in call_url


# ---------------------------------------------------------------------------
# web_search
# ---------------------------------------------------------------------------
class TestWebSearch:
    _RESULTS = [
        {"title": "Title A", "body": "Body A", "href": "https://a.com"},
        {"title": "Title B", "body": "Body B", "href": "https://b.com"},
        {"title": "Title C", "body": "Body C", "href": "https://c.com"},
    ]

    def test_returns_formatted_results(self):
        with patch("app.backend.tools.web_tools.DDGS") as MockDDGS:
            MockDDGS.return_value.__enter__.return_value.text.return_value = self._RESULTS
            result = web_search("Python tutorial")
        assert "Title A" in result
        assert "https://a.com" in result
        assert "Body B" in result

    def test_no_results_returns_no_results_message(self):
        with patch("app.backend.tools.web_tools.DDGS") as MockDDGS:
            MockDDGS.return_value.__enter__.return_value.text.return_value = []
            result = web_search("xyzzy123nonsense")
        assert "No results found" in result

    def test_returns_error_string_on_exception(self):
        with patch(
            "app.backend.tools.web_tools.DDGS",
            side_effect=RuntimeError("ddgs error"),
        ):
            result = web_search("test")
        assert "Search failed" in result
        assert "ddgs error" in result

    def test_max_results_requested_is_three(self):
        """The function should request at most 3 results from DDGS."""
        with patch("app.backend.tools.web_tools.DDGS") as MockDDGS:
            mock_ddgs_instance = MockDDGS.return_value.__enter__.return_value
            mock_ddgs_instance.text.return_value = self._RESULTS
            web_search("anything")
        mock_ddgs_instance.text.assert_called_once_with("anything", max_results=3)

    def test_output_is_stripped(self):
        with patch("app.backend.tools.web_tools.DDGS") as MockDDGS:
            MockDDGS.return_value.__enter__.return_value.text.return_value = self._RESULTS
            result = web_search("test")
        assert result == result.strip()

    def test_returns_error_string_on_network_timeout(self):
        import requests as req
        with patch(
            "app.backend.tools.web_tools.DDGS",
            side_effect=req.exceptions.Timeout("search timed out"),
        ):
            result = web_search("latest news")
        assert "Search failed" in result
