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
    clipboard_write,
    get_active_window,
    get_all_windows,
    set_volume,
    adjust_volume,
    mute_unmute_mic,
    set_brightness,
    adjust_brightness,
    take_screenshot,
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
# clipboard_write
# ---------------------------------------------------------------------------
class TestClipboardWrite:
    def test_calls_pyperclip_copy_with_given_value(self):
        """pyperclip.copy must be called exactly once with the value passed in."""
        with patch("app.backend.tools.system_tools.pyperclip.copy") as mock_copy:
            clipboard_write("mypassword")
        mock_copy.assert_called_once_with("mypassword")

    def test_returns_success_string_on_success(self):
        """On a successful copy, the function must return a confirmation string."""
        with patch("app.backend.tools.system_tools.pyperclip.copy"):
            result = clipboard_write("abc123")
        assert result == "Copied to clipboard."

    def test_handles_pyperclip_exception_gracefully(self):
        """If pyperclip.copy raises, the exception must NOT propagate;
        a failure string must be returned and log_error must be called."""
        with (
            patch(
                "app.backend.tools.system_tools.pyperclip.copy",
                side_effect=RuntimeError("no clipboard"),
            ),
            patch("app.backend.tools.system_tools.log_error") as mock_log,
        ):
            result = clipboard_write("somevalue")
        assert "Failed to copy to clipboard" in result
        assert "no clipboard" in result
        mock_log.assert_called()

    def test_does_not_call_pyperclip_paste_or_read(self):
        """clipboard_write is a write-only tool — it must never call pyperclip.paste()
        as a side effect (scope discipline)."""
        with (
            patch("app.backend.tools.system_tools.pyperclip.copy"),
            patch("app.backend.tools.system_tools.pyperclip.paste") as mock_paste,
        ):
            clipboard_write("onlywrite")
        mock_paste.assert_not_called()


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


# ---------------------------------------------------------------------------
# set_volume
# ---------------------------------------------------------------------------
class TestSetVolume:
    def _make_mock_volume(self):
        """Return a MagicMock that stands in for IAudioEndpointVolume."""
        return MagicMock()

    def test_happy_path_sets_correct_level(self):
        mock_vol = self._make_mock_volume()
        with patch("app.backend.tools.system_tools._get_master_volume_interface", return_value=mock_vol):
            result = set_volume(60)
        mock_vol.SetMasterVolumeLevelScalar.assert_called_once_with(0.60, None)
        assert "60%" in result

    def test_clamps_level_above_100(self):
        mock_vol = self._make_mock_volume()
        with patch("app.backend.tools.system_tools._get_master_volume_interface", return_value=mock_vol):
            result = set_volume(150)
        mock_vol.SetMasterVolumeLevelScalar.assert_called_once_with(1.0, None)
        assert "100%" in result

    def test_clamps_level_below_0(self):
        mock_vol = self._make_mock_volume()
        with patch("app.backend.tools.system_tools._get_master_volume_interface", return_value=mock_vol):
            result = set_volume(-20)
        mock_vol.SetMasterVolumeLevelScalar.assert_called_once_with(0.0, None)
        assert "0%" in result

    def test_exception_returns_graceful_error(self):
        with patch(
            "app.backend.tools.system_tools._get_master_volume_interface",
            side_effect=RuntimeError("COM failure"),
        ):
            result = set_volume(50)
        assert "Failed to set volume" in result
        assert "COM failure" in result


# ---------------------------------------------------------------------------
# adjust_volume
# ---------------------------------------------------------------------------
class TestAdjustVolume:
    def _make_mock_volume(self, current_scalar: float):
        mock_vol = MagicMock()
        mock_vol.GetMasterVolumeLevelScalar.return_value = current_scalar
        return mock_vol

    def test_direction_up_increases_by_10(self):
        mock_vol = self._make_mock_volume(0.50)
        with patch("app.backend.tools.system_tools._get_master_volume_interface", return_value=mock_vol):
            result = adjust_volume("up")
        mock_vol.SetMasterVolumeLevelScalar.assert_called_once_with(0.60, None)
        assert "increased" in result
        assert "60%" in result

    def test_direction_down_decreases_by_10(self):
        mock_vol = self._make_mock_volume(0.50)
        with patch("app.backend.tools.system_tools._get_master_volume_interface", return_value=mock_vol):
            result = adjust_volume("down")
        mock_vol.SetMasterVolumeLevelScalar.assert_called_once_with(0.40, None)
        assert "decreased" in result
        assert "40%" in result

    def test_clamps_to_100_when_near_max(self):
        mock_vol = self._make_mock_volume(0.95)
        with patch("app.backend.tools.system_tools._get_master_volume_interface", return_value=mock_vol):
            result = adjust_volume("up")
        mock_vol.SetMasterVolumeLevelScalar.assert_called_once_with(1.0, None)
        assert "100%" in result

    def test_clamps_to_0_when_near_min(self):
        mock_vol = self._make_mock_volume(0.05)
        with patch("app.backend.tools.system_tools._get_master_volume_interface", return_value=mock_vol):
            result = adjust_volume("down")
        mock_vol.SetMasterVolumeLevelScalar.assert_called_once_with(0.0, None)
        assert "0%" in result

    def test_invalid_direction_returns_error_message(self):
        mock_vol = self._make_mock_volume(0.50)
        with patch("app.backend.tools.system_tools._get_master_volume_interface", return_value=mock_vol):
            result = adjust_volume("sideways")
        assert "Invalid direction" in result
        mock_vol.SetMasterVolumeLevelScalar.assert_not_called()

    def test_exception_returns_graceful_error(self):
        with patch(
            "app.backend.tools.system_tools._get_master_volume_interface",
            side_effect=RuntimeError("COM gone"),
        ):
            result = adjust_volume("up")
        assert "Failed to adjust volume" in result
        assert "COM gone" in result


# ---------------------------------------------------------------------------
# mute_unmute_mic
# ---------------------------------------------------------------------------
class TestMuteUnmuteMic:
    def _make_mic_chain(self, current_mute: bool):
        """
        Build the mock chain:
          AudioUtilities.GetMicrophone() → raw_mic (IMMDevice)
          raw_mic.Activate(...)          → iface
          iface.QueryInterface(...)      → volume_ctl
          volume_ctl.GetMute()           → current_mute
        """
        volume_ctl = MagicMock()
        volume_ctl.GetMute.return_value = current_mute

        iface = MagicMock()
        iface.QueryInterface.return_value = volume_ctl

        raw_mic = MagicMock()
        raw_mic.Activate.return_value = iface

        return raw_mic, volume_ctl

    def test_unmuted_mic_becomes_muted(self):
        raw_mic, volume_ctl = self._make_mic_chain(current_mute=False)
        import sys
        sys.modules["pycaw.pycaw"].AudioUtilities.GetMicrophone.return_value = raw_mic
        result = mute_unmute_mic()
        volume_ctl.SetMute.assert_called_once_with(True, None)
        assert "Microphone muted" in result

    def test_muted_mic_becomes_unmuted(self):
        raw_mic, volume_ctl = self._make_mic_chain(current_mute=True)
        import sys
        sys.modules["pycaw.pycaw"].AudioUtilities.GetMicrophone.return_value = raw_mic
        result = mute_unmute_mic()
        volume_ctl.SetMute.assert_called_once_with(False, None)
        assert "Microphone unmuted" in result

    def test_no_microphone_returns_graceful_message(self):
        import sys
        sys.modules["pycaw.pycaw"].AudioUtilities.GetMicrophone.return_value = None
        result = mute_unmute_mic()
        assert "No default microphone" in result

    def test_exception_returns_graceful_error(self):
        import sys
        sys.modules["pycaw.pycaw"].AudioUtilities.GetMicrophone.side_effect = RuntimeError("no audio")
        result = mute_unmute_mic()
        assert "Failed to toggle microphone mute" in result
        assert "no audio" in result
        # Reset side_effect so it does not bleed into other tests
        sys.modules["pycaw.pycaw"].AudioUtilities.GetMicrophone.side_effect = None


# ---------------------------------------------------------------------------
# set_brightness
# ---------------------------------------------------------------------------
class TestSetBrightness:
    def test_happy_path_sets_correct_level(self):
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.reset_mock()
        result = set_brightness(70)
        sbc.set_brightness.assert_called_once_with(70)
        assert "70%" in result

    def test_clamps_level_above_100(self):
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.reset_mock()
        result = set_brightness(120)
        sbc.set_brightness.assert_called_once_with(100)
        assert "100%" in result

    def test_clamps_level_below_0(self):
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.reset_mock()
        result = set_brightness(-10)
        sbc.set_brightness.assert_called_once_with(0)
        assert "0%" in result

    def test_exception_returns_graceful_error(self):
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.side_effect = RuntimeError("driver error")
        result = set_brightness(50)
        assert "Failed to set brightness" in result
        assert "driver error" in result
        sbc.set_brightness.side_effect = None


# ---------------------------------------------------------------------------
# adjust_brightness
# ---------------------------------------------------------------------------
class TestAdjustBrightness:
    def _set_current(self, level: int):
        """Configure the sbc stub so get_brightness() returns [level]."""
        import sys
        sys.modules["screen_brightness_control"].get_brightness.return_value = [level]

    def test_direction_up_increases_by_10(self):
        self._set_current(50)
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.reset_mock()
        result = adjust_brightness("up")
        sbc.set_brightness.assert_called_once_with(60)
        assert "increased" in result
        assert "60%" in result

    def test_direction_down_decreases_by_10(self):
        self._set_current(50)
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.reset_mock()
        result = adjust_brightness("down")
        sbc.set_brightness.assert_called_once_with(40)
        assert "decreased" in result
        assert "40%" in result

    def test_empty_get_brightness_falls_back_to_default_50(self):
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.get_brightness.return_value = []
        sbc.set_brightness.reset_mock()
        result = adjust_brightness("up")
        # default current=50 → up → 60
        sbc.set_brightness.assert_called_once_with(60)
        assert "60%" in result

    def test_clamps_to_100_when_near_max(self):
        self._set_current(95)
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.reset_mock()
        result = adjust_brightness("up")
        sbc.set_brightness.assert_called_once_with(100)
        assert "100%" in result

    def test_clamps_to_0_when_near_min(self):
        self._set_current(5)
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.reset_mock()
        result = adjust_brightness("down")
        sbc.set_brightness.assert_called_once_with(0)
        assert "0%" in result

    def test_invalid_direction_returns_error_message(self):
        self._set_current(50)
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.set_brightness.reset_mock()
        result = adjust_brightness("left")
        assert "Invalid direction" in result
        sbc.set_brightness.assert_not_called()

    def test_exception_returns_graceful_error(self):
        import sys
        sbc = sys.modules["screen_brightness_control"]
        sbc.get_brightness.side_effect = RuntimeError("wmi failure")
        result = adjust_brightness("up")
        assert "Failed to adjust brightness" in result
        assert "wmi failure" in result
        sbc.get_brightness.side_effect = None

class TestTakeScreenshot:
    @patch("app.backend.tools.system_tools.pyautogui")
    @patch("app.backend.tools.system_tools.os.makedirs")
    @patch("app.backend.tools.system_tools.datetime")
    def test_success_case(self, mock_datetime, mock_makedirs, mock_pyautogui):
        import datetime
        fake_now = datetime.datetime(2026, 7, 12, 10, 47, 3)
        mock_datetime.datetime.now.return_value = fake_now
        
        result = take_screenshot()
        
        expected_path = r"C:\Users\sithi\Pictures\Screenshots\Screenshot 2026-07-12 104703.png"
        
        mock_makedirs.assert_called_once_with(r"C:\Users\sithi\Pictures\Screenshots", exist_ok=True)
        mock_pyautogui.screenshot.assert_called_once_with(expected_path)
        assert result == f"Screenshot saved to {expected_path}."

    @patch("app.backend.tools.system_tools.pyautogui")
    @patch("app.backend.tools.system_tools.os.makedirs")
    def test_exception_safety(self, mock_makedirs, mock_pyautogui):
        import pyautogui
        mock_pyautogui.screenshot.side_effect = pyautogui.PyAutoGUIException("test error")
        
        result = take_screenshot()
        
        assert result.startswith("Failed to take screenshot:")
        assert "test error" in result

# ---------------------------------------------------------------------------
# Power Controls
# ---------------------------------------------------------------------------
class TestLockScreen:
    def test_lock_screen_calls_lock_work_station(self):
        """Happy path: LockWorkStation() returns non-zero (success)."""
        from app.backend.tools.system_tools import lock_screen
        with patch("app.backend.tools.system_tools.ctypes") as mock_ctypes:
            mock_ctypes.windll.user32.LockWorkStation.return_value = 1
            result = lock_screen()
        mock_ctypes.windll.user32.LockWorkStation.assert_called_once()
        assert result == "Locked."

    def test_lock_screen_returns_error_when_api_returns_zero(self):
        """LockWorkStation() returns 0 → graceful failure message (no exception)."""
        from app.backend.tools.system_tools import lock_screen
        with patch("app.backend.tools.system_tools.ctypes") as mock_ctypes:
            mock_ctypes.windll.user32.LockWorkStation.return_value = 0
            mock_ctypes.get_last_error.return_value = 5  # ERROR_ACCESS_DENIED
            result = lock_screen()
        assert "Failed to lock screen" in result
        assert "LockWorkStation returned 0" in result

    def test_lock_screen_exception_safety(self):
        """If LockWorkStation raises an unexpected exception, a graceful error is returned."""
        from app.backend.tools.system_tools import lock_screen
        with patch("app.backend.tools.system_tools.ctypes") as mock_ctypes:
            mock_ctypes.windll.user32.LockWorkStation.side_effect = RuntimeError("ctypes broken")
            result = lock_screen()
        assert "Failed to lock screen" in result

    def test_request_shutdown(self):
        from app.backend.tools.system_tools import request_shutdown
        from app.backend.chat import confirmation
        confirmation.clear_confirmation()
        result = request_shutdown()
        assert "Say the code" in result
        pending = confirmation.get_pending()
        assert pending is not None
        assert pending["action"] == "shutdown"
        assert pending["token"] in result

    def test_request_restart(self):
        from app.backend.tools.system_tools import request_restart
        from app.backend.chat import confirmation
        confirmation.clear_confirmation()
        result = request_restart()
        assert "Say the code" in result
        pending = confirmation.get_pending()
        assert pending is not None
        assert pending["action"] == "restart"
        assert pending["token"] in result

    @patch("app.backend.tools.system_tools.os.system")
    def test_shutdown_unconfirmed(self, mock_os_system):
        from app.backend.tools.system_tools import shutdown_system
        from app.backend.chat import confirmation
        confirmation.clear_confirmation()
        result = shutdown_system(token="0000")
        mock_os_system.assert_not_called()
        assert "Confirmation failed" in result

    @patch("app.backend.tools.system_tools.os.system")
    def test_shutdown_confirmed(self, mock_os_system):
        from app.backend.tools.system_tools import shutdown_system
        from app.backend.chat import confirmation
        token = confirmation.request_confirmation("shutdown")
        result = shutdown_system(token=token)
        mock_os_system.assert_called_once_with("shutdown /s /t 0")
        assert result == "Shutting down now."
        assert confirmation.get_pending() is None

    @patch("app.backend.tools.system_tools.os.system")
    def test_restart_unconfirmed(self, mock_os_system):
        from app.backend.tools.system_tools import restart_system
        from app.backend.chat import confirmation
        confirmation.clear_confirmation()
        result = restart_system(token="0000")
        mock_os_system.assert_not_called()
        assert "Confirmation failed" in result

    @patch("app.backend.tools.system_tools.os.system")
    def test_restart_confirmed(self, mock_os_system):
        from app.backend.tools.system_tools import restart_system
        from app.backend.chat import confirmation
        token = confirmation.request_confirmation("restart")
        result = restart_system(token=token)
        mock_os_system.assert_called_once_with("shutdown /r /t 0")
        assert result == "Restarting now."
        assert confirmation.get_pending() is None

class TestConfirmation:
    def test_request_confirmation(self):
        from app.backend.chat import confirmation
        confirmation.clear_confirmation()
        token = confirmation.request_confirmation("shutdown")
        assert len(token) == 4
        assert token.isdigit()
        pending = confirmation.get_pending()
        assert pending is not None
        assert pending["action"] == "shutdown"
        assert pending["token"] == token

    @patch("app.backend.chat.confirmation.time")
    def test_check_confirmation_success(self, mock_time):
        import time
        from app.backend.chat import confirmation
        mock_time.time.return_value = 1000
        confirmation.clear_confirmation()
        token = confirmation.request_confirmation("shutdown")
        assert confirmation.check_confirmation("shutdown", token) is True
        assert confirmation.get_pending() is None

    @patch("app.backend.chat.confirmation.time")
    def test_check_confirmation_expired(self, mock_time):
        from app.backend.chat import confirmation
        mock_time.time.return_value = 1000
        confirmation.clear_confirmation()
        token = confirmation.request_confirmation("shutdown")
        mock_time.time.return_value = 2000  # past 60s
        assert confirmation.check_confirmation("shutdown", token) is False
        assert confirmation.get_pending() is None

    def test_check_confirmation_wrong_action(self):
        from app.backend.chat import confirmation
        confirmation.clear_confirmation()
        token = confirmation.request_confirmation("shutdown")
        assert confirmation.check_confirmation("restart", token) is False
        assert confirmation.get_pending() is not None

    def test_check_confirmation_wrong_token(self):
        from app.backend.chat import confirmation
        confirmation.clear_confirmation()
        token = confirmation.request_confirmation("shutdown")
        assert confirmation.check_confirmation("shutdown", "0000") is False
        assert confirmation.get_pending() is not None

    def test_check_confirmation_no_pending(self):
        from app.backend.chat import confirmation
        confirmation.clear_confirmation()
        assert confirmation.check_confirmation("shutdown", "1234") is False
