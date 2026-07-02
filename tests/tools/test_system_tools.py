"""Unit tests for app/backend/tools/system_tools.py.

All external dependencies (os.startfile, subprocess, pyautogui, psutil,
pyperclip, pygetwindow) are mocked.  No real applications are launched, no
real system state is read.

NOTE: Because tests/tools/conftest.py stubs @tool as a no-op decorator, the
tool functions are plain Python functions here. They are called directly.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.backend.tools.system_tools import (
    open_application,
    open_file,
    get_battery_status,
    read_clipboard,
    get_active_window,
    get_all_windows,
)


# ---------------------------------------------------------------------------
# open_application
# ---------------------------------------------------------------------------
class TestOpenApplication:
    def test_os_startfile_succeeds(self):
        """Happy path: os.startfile works on first try."""
        with patch("app.backend.tools.system_tools.os.startfile") as mock_sf:
            result = open_application("notepad")
        mock_sf.assert_called_once_with("notepad")
        assert "Opened notepad successfully" in result

    def test_falls_back_to_subprocess_when_startfile_fails(self):
        """If os.startfile raises, subprocess.Popen is tried next."""
        with (
            patch("app.backend.tools.system_tools.os.startfile", side_effect=OSError("no")),
            patch("app.backend.tools.system_tools.subprocess.Popen") as mock_popen,
        ):
            result = open_application("notepad")
        mock_popen.assert_called_once_with("notepad")
        assert "Opened notepad successfully" in result

    def test_falls_back_to_pyautogui_when_subprocess_fails(self):
        """If both os.startfile and subprocess fail, pyautogui search is used."""
        with (
            patch("app.backend.tools.system_tools.os.startfile", side_effect=OSError),
            patch("app.backend.tools.system_tools.subprocess.Popen", side_effect=OSError),
            patch("app.backend.tools.system_tools.pyautogui.hotkey") as mock_hotkey,
            patch("app.backend.tools.system_tools.pyautogui.typewrite"),
            patch("app.backend.tools.system_tools.pyautogui.press"),
            patch("app.backend.tools.system_tools.time.sleep"),
        ):
            result = open_application("notepad")
        mock_hotkey.assert_called_once_with("win")
        assert "via Windows search" in result

    def test_returns_error_string_when_all_methods_fail(self):
        """If all three open methods fail, a friendly error string is returned."""
        with (
            patch("app.backend.tools.system_tools.os.startfile", side_effect=OSError),
            patch("app.backend.tools.system_tools.subprocess.Popen", side_effect=OSError),
            patch(
                "app.backend.tools.system_tools.pyautogui.hotkey",
                side_effect=RuntimeError("gui error"),
            ),
            patch("app.backend.tools.system_tools.time.sleep"),
        ):
            result = open_application("badapp")
        assert "Failed to open badapp" in result
        assert "gui error" in result

    def test_empty_app_name_attempts_open_and_returns_result(self):
        """Edge-case: empty string is forwarded; outcome depends on OS behavior (mocked)."""
        with patch("app.backend.tools.system_tools.os.startfile") as mock_sf:
            result = open_application("")
        mock_sf.assert_called_once_with("")
        assert "Opened" in result


# ---------------------------------------------------------------------------
# open_file
# ---------------------------------------------------------------------------
class TestOpenFile:
    def test_success(self):
        with patch("app.backend.tools.system_tools.os.startfile") as mock_sf:
            result = open_file("report.pdf")
        mock_sf.assert_called_once_with("report.pdf")
        assert "Opened report.pdf successfully" in result

    def test_file_not_found_returns_error_string(self):
        with patch(
            "app.backend.tools.system_tools.os.startfile",
            side_effect=FileNotFoundError("no such file"),
        ):
            result = open_file("missing.pdf")
        assert "Failed to open missing.pdf" in result
        assert "no such file" in result

    def test_os_error_returns_error_string(self):
        with patch(
            "app.backend.tools.system_tools.os.startfile",
            side_effect=OSError("permission denied"),
        ):
            result = open_file("locked.pdf")
        assert "Failed to open locked.pdf" in result


# ---------------------------------------------------------------------------
# get_battery_status
# ---------------------------------------------------------------------------
class TestGetBatteryStatus:
    def _make_battery(self, percent, plugged):
        b = MagicMock()
        b.percent = percent
        b.power_plugged = plugged
        return b

    def test_returns_charging_status(self):
        with patch(
            "app.backend.tools.system_tools.psutil.sensors_battery",
            return_value=self._make_battery(85, True),
        ):
            result = get_battery_status()
        assert "85%" in result
        assert "charging" in result

    def test_returns_not_charging_status(self):
        with patch(
            "app.backend.tools.system_tools.psutil.sensors_battery",
            return_value=self._make_battery(42, False),
        ):
            result = get_battery_status()
        assert "42%" in result
        assert "not charging" in result

    def test_returns_unavailable_when_battery_is_none(self):
        with patch(
            "app.backend.tools.system_tools.psutil.sensors_battery",
            return_value=None,
        ):
            result = get_battery_status()
        assert "not available" in result

    # -----------------------------------------------------------------------
    # BUG DEMONSTRATION — psutil raising propagates unhandled
    # -----------------------------------------------------------------------
    def test_psutil_exception_returns_graceful_fallback(self):
        """
        FIX VERIFIED: get_battery_status now wraps psutil.sensors_battery() in
        try/except.  When psutil raises, a graceful fallback string is returned
        and the exception is logged — the caller no longer crashes.
        """
        with patch(
            "app.backend.tools.system_tools.psutil.sensors_battery",
            side_effect=RuntimeError("psutil internal error"),
        ):
            result = get_battery_status()
        assert "unavailable" in result.lower()


# ---------------------------------------------------------------------------
# read_clipboard
# ---------------------------------------------------------------------------
class TestReadClipboard:
    def test_returns_clipboard_content(self):
        with patch("app.backend.tools.system_tools.pyperclip.paste", return_value="hello world"):
            result = read_clipboard()
        assert "hello world" in result

    def test_returns_empty_message_when_clipboard_empty(self):
        with patch("app.backend.tools.system_tools.pyperclip.paste", return_value=""):
            result = read_clipboard()
        assert "empty" in result.lower()

    def test_returns_empty_message_for_none(self):
        with patch("app.backend.tools.system_tools.pyperclip.paste", return_value=None):
            result = read_clipboard()
        assert "empty" in result.lower()


# ---------------------------------------------------------------------------
# get_active_window
# ---------------------------------------------------------------------------
class TestGetActiveWindow:
    def test_returns_window_title(self):
        mock_window = MagicMock()
        mock_window.title = "Visual Studio Code"
        with patch("app.backend.tools.system_tools.gw.getActiveWindow", return_value=mock_window):
            result = get_active_window()
        assert "Visual Studio Code" in result

    def test_returns_no_window_message_when_none(self):
        with patch("app.backend.tools.system_tools.gw.getActiveWindow", return_value=None):
            result = get_active_window()
        assert "No active window" in result


# ---------------------------------------------------------------------------
# get_all_windows
# ---------------------------------------------------------------------------
class TestGetAllWindows:
    def _make_win(self, title):
        w = MagicMock()
        w.title = title
        return w

    def test_returns_list_of_window_titles(self):
        wins = [self._make_win("Chrome"), self._make_win("Notepad"), self._make_win("  ")]
        with patch("app.backend.tools.system_tools.gw.getAllWindows", return_value=wins):
            result = get_all_windows()
        assert "Chrome" in result
        assert "Notepad" in result
        # blank-title window should be filtered out
        assert result.count("-") == 2

    def test_returns_no_windows_message_when_all_empty(self):
        wins = [self._make_win(""), self._make_win("   ")]
        with patch("app.backend.tools.system_tools.gw.getAllWindows", return_value=wins):
            result = get_all_windows()
        assert "No open windows" in result

    def test_returns_no_windows_message_when_list_empty(self):
        with patch("app.backend.tools.system_tools.gw.getAllWindows", return_value=[]):
            result = get_all_windows()
        assert "No open windows" in result
