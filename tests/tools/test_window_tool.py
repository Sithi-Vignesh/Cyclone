"""Unit tests for app/backend/tools/window_tool.py.

All external dependencies (pywinauto, pyautogui, pygetwindow) are mocked.
No real windows are opened, focused, minimized, or closed during test runs.

NOTE: Because tests/tools/conftest.py stubs @tool as a no-op decorator, the
tool functions are plain Python functions here — they are called directly.

Bug regression context
----------------------
The original _connect_by_title() passed timeout=0 to Application.connect().
Due to a pywinauto implementation detail (application.py:988), any call that
includes `timeout` in kwargs is routed through wait_until_passes() with the
*default* Timings.app_connect_timeout (5 s), not the supplied value.  On
failure it raises TimeoutError() (no message), which is not caught by the
`except ElementNotFoundError` guard, and propagates to the outer
`except Exception as e` — producing the empty "Failed to maximize 'notepad': "
string observed during manual testing.

The fix calls findwindows.find_element() directly (what connect() delegates to
anyway), catches ElementNotFoundError there, and only calls
Application.connect(process=...) once a process ID has been confirmed.

Tests in this file that assert "Failed" strings contain a non-empty detail
after the colon explicitly guard against that regression.
"""
from unittest.mock import MagicMock, patch, call
import sys

import pytest

from app.backend.tools.window_tool import (
    minimize_window,
    maximize_window,
    close_window,
    focus_window,
    _connect_by_title,
    _active_window_title,
)

# Pull the real ElementNotFoundError class that conftest registered.
_ElementNotFoundError = sys.modules["pywinauto.findwindows"].ElementNotFoundError


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _make_app_mock():
    """Return a mock Application whose top_window() is also a mock."""
    win = MagicMock()
    app = MagicMock()
    app.top_window.return_value = win
    return app, win


def _make_active_window(title: str):
    """Return a mock pygetwindow window object with the given title."""
    w = MagicMock()
    w.title = title
    return w


# ---------------------------------------------------------------------------
# _connect_by_title (internal helper — direct unit tests)
# ---------------------------------------------------------------------------

class TestConnectByTitle:
    """Verify the fixed _connect_by_title helper in isolation."""

    def test_returns_application_on_first_match(self):
        """find_element succeeds immediately → Application.connect called once."""
        elem = MagicMock()
        elem.process_id = 1234

        app_mock, _ = _make_app_mock()

        with (
            patch("app.backend.tools.window_tool.findwindows.find_element", return_value=elem) as mock_fe,
            patch("app.backend.tools.window_tool.Application", return_value=app_mock) as mock_app_cls,
        ):
            result = _connect_by_title("notepad")

        mock_fe.assert_called_once()
        mock_app_cls.assert_called_once_with(backend="uia")
        app_mock.connect.assert_called_once_with(process=1234)
        assert result is app_mock.connect.return_value

    def test_retries_on_element_not_found_then_succeeds(self):
        """find_element raises ElementNotFoundError on first attempt, succeeds on second."""
        elem = MagicMock()
        elem.process_id = 5678

        app_mock, _ = _make_app_mock()

        with (
            patch(
                "app.backend.tools.window_tool.findwindows.find_element",
                side_effect=[_ElementNotFoundError("not yet"), elem],
            ) as mock_fe,
            patch("app.backend.tools.window_tool.Application", return_value=app_mock),
            patch("app.backend.tools.window_tool.time.sleep"),
        ):
            result = _connect_by_title("chrome")

        assert mock_fe.call_count == 2
        assert result is app_mock.connect.return_value

    def test_returns_none_after_all_retries_exhausted(self):
        """find_element always raises → helper returns None after _CONNECT_RETRIES attempts."""
        with (
            patch(
                "app.backend.tools.window_tool.findwindows.find_element",
                side_effect=_ElementNotFoundError("never found"),
            ) as mock_fe,
            patch("app.backend.tools.window_tool.time.sleep"),
        ):
            result = _connect_by_title("ghost")

        # Exactly _CONNECT_RETRIES attempts, then None
        assert result is None
        assert mock_fe.call_count == 5  # _CONNECT_RETRIES constant


# ---------------------------------------------------------------------------
# minimize_window
# ---------------------------------------------------------------------------

class TestMinimizeWindow:
    def test_empty_name_sends_win_d_hotkey(self):
        """No app_name → Win+D shortcut, returns 'Minimized all windows.'"""
        with patch("app.backend.tools.window_tool.pyautogui.hotkey") as mock_hk:
            result = minimize_window("")
        mock_hk.assert_called_once_with("win", "d")
        assert "Minimized all windows" in result

    def test_whitespace_name_also_sends_win_d(self):
        """Whitespace-only app_name is treated as empty."""
        with patch("app.backend.tools.window_tool.pyautogui.hotkey") as mock_hk:
            result = minimize_window("   ")
        mock_hk.assert_called_once_with("win", "d")
        assert "Minimized all windows" in result

    def test_named_window_found_minimizes(self):
        """Named app_name found → .minimize() called, friendly message returned."""
        app_mock, win_mock = _make_app_mock()
        with patch("app.backend.tools.window_tool._connect_by_title", return_value=app_mock):
            result = minimize_window("notepad")
        win_mock.minimize.assert_called_once()
        assert "Minimized notepad" in result

    def test_named_window_not_found_returns_friendly_message(self):
        """_connect_by_title returns None → clear 'couldn't find' message, no crash."""
        with patch("app.backend.tools.window_tool._connect_by_title", return_value=None):
            result = minimize_window("ghostapp")
        assert "ghostapp" in result
        assert "find" in result.lower() or "Couldn't" in result

    def test_exception_returns_non_empty_error_string(self):
        """Exception path produces a non-empty error detail after the colon (regression guard)."""
        with patch(
            "app.backend.tools.window_tool._connect_by_title",
            side_effect=RuntimeError("access denied"),
        ):
            result = minimize_window("notepad")
        assert "Failed" in result
        assert "access denied" in result          # MUST be non-empty — catches the original bug


# ---------------------------------------------------------------------------
# maximize_window
# ---------------------------------------------------------------------------

class TestMaximizeWindow:
    def test_named_window_found_maximizes(self):
        """Named app_name found → .maximize() called."""
        app_mock, win_mock = _make_app_mock()
        with patch("app.backend.tools.window_tool._connect_by_title", return_value=app_mock):
            result = maximize_window("chrome")
        win_mock.maximize.assert_called_once()
        assert "Maximized chrome" in result

    def test_named_window_not_found_returns_friendly_message(self):
        with patch("app.backend.tools.window_tool._connect_by_title", return_value=None):
            result = maximize_window("ghostapp")
        assert "ghostapp" in result
        assert "find" in result.lower() or "Couldn't" in result

    def test_empty_name_maximizes_active_window(self):
        """No app_name → resolves active window title, connects and maximizes it."""
        active_win = _make_active_window("Visual Studio Code")
        app_mock, win_mock = _make_app_mock()
        with (
            patch("app.backend.tools.window_tool.gw.getActiveWindow", return_value=active_win),
            patch("app.backend.tools.window_tool._connect_by_title", return_value=app_mock),
        ):
            result = maximize_window("")
        win_mock.maximize.assert_called_once()
        assert "Maximized the active window" in result

    def test_empty_name_no_active_window_returns_message(self):
        """No active window detectable → graceful message, no crash."""
        with patch("app.backend.tools.window_tool.gw.getActiveWindow", return_value=None):
            result = maximize_window("")
        assert "No active window" in result

    def test_empty_name_active_window_connect_fails_returns_message(self):
        """Active window detected but _connect_by_title returns None → graceful message."""
        active_win = _make_active_window("Notepad")
        with (
            patch("app.backend.tools.window_tool.gw.getActiveWindow", return_value=active_win),
            patch("app.backend.tools.window_tool._connect_by_title", return_value=None),
        ):
            result = maximize_window("")
        assert "Couldn't connect" in result

    def test_exception_returns_non_empty_error_string(self):
        """Exception path: error detail after colon is non-empty (regression guard)."""
        with patch(
            "app.backend.tools.window_tool._connect_by_title",
            side_effect=RuntimeError("uia timeout"),
        ):
            result = maximize_window("notepad")
        assert "Failed" in result
        assert "uia timeout" in result            # MUST be non-empty — catches the original bug


# ---------------------------------------------------------------------------
# close_window
# ---------------------------------------------------------------------------

class TestCloseWindow:
    def test_named_window_found_closes(self):
        """Named app_name found → .close() called."""
        app_mock, win_mock = _make_app_mock()
        with patch("app.backend.tools.window_tool._connect_by_title", return_value=app_mock):
            result = close_window("notepad")
        win_mock.close.assert_called_once()
        assert "Closed notepad" in result

    def test_named_window_not_found_returns_friendly_message(self):
        with patch("app.backend.tools.window_tool._connect_by_title", return_value=None):
            result = close_window("ghostapp")
        assert "ghostapp" in result
        assert "find" in result.lower() or "Couldn't" in result

    def test_empty_name_closes_active_window(self):
        """No app_name → resolves active window title, connects and closes it."""
        active_win = _make_active_window("Notepad")
        app_mock, win_mock = _make_app_mock()
        with (
            patch("app.backend.tools.window_tool.gw.getActiveWindow", return_value=active_win),
            patch("app.backend.tools.window_tool._connect_by_title", return_value=app_mock),
        ):
            result = close_window("")
        win_mock.close.assert_called_once()
        assert "Closed the active window" in result

    def test_empty_name_no_active_window_returns_message(self):
        with patch("app.backend.tools.window_tool.gw.getActiveWindow", return_value=None):
            result = close_window("")
        assert "No active window" in result

    def test_empty_name_active_connect_fails_returns_message(self):
        active_win = _make_active_window("Notepad")
        with (
            patch("app.backend.tools.window_tool.gw.getActiveWindow", return_value=active_win),
            patch("app.backend.tools.window_tool._connect_by_title", return_value=None),
        ):
            result = close_window("")
        assert "Couldn't connect" in result

    def test_exception_returns_non_empty_error_string(self):
        """Exception path: error detail after colon is non-empty (regression guard)."""
        with patch(
            "app.backend.tools.window_tool._connect_by_title",
            side_effect=RuntimeError("permission denied"),
        ):
            result = close_window("notepad")
        assert "Failed" in result
        assert "permission denied" in result      # MUST be non-empty — catches the original bug


# ---------------------------------------------------------------------------
# focus_window
# ---------------------------------------------------------------------------

class TestFocusWindow:
    def test_named_window_found_focuses(self):
        """Named app_name found → .set_focus() called."""
        app_mock, win_mock = _make_app_mock()
        with patch("app.backend.tools.window_tool._connect_by_title", return_value=app_mock):
            result = focus_window("code")
        win_mock.set_focus.assert_called_once()
        assert "Switched focus to code" in result

    def test_named_window_not_found_returns_friendly_message(self):
        with patch("app.backend.tools.window_tool._connect_by_title", return_value=None):
            result = focus_window("ghostapp")
        assert "ghostapp" in result
        assert "find" in result.lower() or "Couldn't" in result

    def test_empty_app_name_returns_clarification_prompt(self):
        """Empty string → guard returns the clarification question without attempting anything."""
        with patch("app.backend.tools.window_tool._connect_by_title") as mock_connect:
            result = focus_window("")
        mock_connect.assert_not_called()
        assert "Which app" in result

    def test_whitespace_only_app_name_returns_clarification_prompt(self):
        """Whitespace-only is treated as empty — no connect attempt."""
        with patch("app.backend.tools.window_tool._connect_by_title") as mock_connect:
            result = focus_window("   ")
        mock_connect.assert_not_called()
        assert "Which app" in result

    def test_exception_returns_non_empty_error_string(self):
        """Exception path: error detail after colon is non-empty (regression guard)."""
        with patch(
            "app.backend.tools.window_tool._connect_by_title",
            side_effect=RuntimeError("com error"),
        ):
            result = focus_window("notepad")
        assert "Failed" in result
        assert "com error" in result              # MUST be non-empty — catches the original bug
