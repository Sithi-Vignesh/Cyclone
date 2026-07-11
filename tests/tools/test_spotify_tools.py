"""Unit tests for app/backend/tools/spotify_tools.py.

pywinauto.Application and time.sleep are mocked throughout.
No real Spotify process is launched or interacted with.

NOTE: Because tests/tools/conftest.py stubs @tool as a no-op decorator,
the tool function is a plain Python function here. Called directly.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.backend.tools.spotify_tools import spotify_play_song


def _make_app_and_window():
    """Helper that returns a mock Application instance and its top_window."""
    mock_window = MagicMock()
    mock_app = MagicMock()
    mock_app.top_window.return_value = mock_window
    return mock_app, mock_window


class TestSpotifyPlaySong:
    def test_happy_path_connects_and_returns_playing_message(self):
        """If Spotify connects immediately, type_keys are sent and success returned."""
        mock_app, mock_window = _make_app_and_window()
        with (
            patch("app.backend.tools.spotify_tools._connect_spotify_window", return_value=mock_app),
            patch("app.backend.tools.spotify_tools.time.sleep"),
        ):
            result = spotify_play_song("Blinding Lights")

        assert "Blinding Lights" in result
        assert "Playing" in result

    def test_returns_timeout_message_when_spotify_never_opens(self):
        """If Spotify window is never found within 30 retries, a friendly message is returned."""
        with (
            patch("app.backend.tools.spotify_tools._connect_spotify_window", return_value=None),
            patch("app.backend.tools.spotify_tools.open_application"),
            patch("app.backend.tools.spotify_tools.time.sleep"),
        ):
            result = spotify_play_song("Levitating")

        assert "didn't open" in result.lower() or "try again" in result.lower()

    def test_exception_after_connect_returns_graceful_fallback(self):
        """
        FIX VERIFIED: The post-connect block is now wrapped in try/except.
        When top_window() (or any subsequent call) raises, a graceful fallback
        string is returned and the exception is logged — the caller no longer
        crashes.
        """
        mock_app = MagicMock()
        mock_app.top_window.side_effect = RuntimeError("window gone")

        with (
            patch("app.backend.tools.spotify_tools._connect_spotify_window", return_value=mock_app),
            patch("app.backend.tools.spotify_tools.time.sleep"),
        ):
            result = spotify_play_song("Shape of You")

        assert "failed to play" in result.lower()
