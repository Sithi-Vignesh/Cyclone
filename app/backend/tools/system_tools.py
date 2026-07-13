from langchain.tools import tool
import ctypes
import os
import datetime
import subprocess
import psutil
import pyperclip
import pygetwindow as gw
import pyautogui
import time
from app.backend.core.error_logger import log_error

@tool
def open_application(app_name: str) -> str:
    """Opens an application on the system by name."""
    try:
        os.startfile(app_name)
        return f"Opened {app_name} successfully."
    except Exception:
        try:
            subprocess.Popen(app_name)
            return f"Opened {app_name} successfully."
        except Exception:
            try:
                pyautogui.hotkey('win')
                time.sleep(1)
                pyautogui.typewrite(app_name, interval=0.05)
                time.sleep(1)
                pyautogui.press('enter')
                return f"Opened {app_name} via Windows search."
            except Exception as e:
                return f"Failed to open {app_name}: {str(e)}"
            
@tool
def open_file(file_name: str) -> str:
    """Opens an files on the system by name. Use this when the user asks to open files in the format of .pdf, .docx, .txt, etc."""
    try:
        os.startfile(file_name)
        return f"Opened {file_name} successfully."
    except Exception as e:
        return f"Failed to open {file_name}: {str(e)}"
    
@tool
def get_battery_status() -> str:
    """Returns the current battery percentage and charging status."""
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return "Battery info not available."
        status = "charging" if battery.power_plugged else "not charging"
        return f"Battery is at {battery.percent:.0f}%, {status}."
    except Exception as e:
        log_error("get_battery_status", e)
        return "Battery status unavailable right now."

@tool
def read_clipboard() -> str:
    """Reads and returns the current text content from the clipboard."""
    text = pyperclip.paste()
    if not text:
        return "Clipboard is empty."
    return f"Clipboard contents: {text}"

@tool
def clipboard_write(value: str) -> str:
    """Writes a value to the Windows clipboard.
    Call with only the specific value to copy (e.g. a password, ID, code, or link) — never pass a full sentence or explanation."""
    try:
        pyperclip.copy(value)
        return "Copied to clipboard."
    except Exception as e:
        log_error("tool:clipboard_write", str(e))
        return f"Failed to copy to clipboard: {e}"

@tool
def get_active_window() -> str:
    """Returns the title of the currently active window."""
    window = gw.getActiveWindow()
    if window is None:
        return "No active window detected."
    return f"Active window: {window.title}"

@tool
def get_all_windows() -> str:
    """Returns a list of all currently open window titles."""
    windows = [w.title for w in gw.getAllWindows() if w.title.strip()]
    if not windows:
        return "No open windows detected."
    return "Open windows:\n" + "\n".join(f"- {w}" for w in windows)


# ---------------------------------------------------------------------------
# Volume & audio controls (pycaw)
# ---------------------------------------------------------------------------

def _get_master_volume_interface():
    """Return the IAudioEndpointVolume COM interface for the default speaker.

    In pycaw>=20251023, AudioUtilities.GetSpeakers() returns an AudioDevice
    wrapper object, not a raw COM IMMDevice. The wrapper exposes an
    .EndpointVolume property that performs the Activate+QueryInterface
    internally (pycaw/utils.py AudioDevice.EndpointVolume). Calling .Activate()
    directly on AudioDevice raises AttributeError — hence the old code broke.
    """
    from pycaw.pycaw import AudioUtilities

    return AudioUtilities.GetSpeakers().EndpointVolume


@tool
def set_volume(level: int) -> str:
    """Sets the system master volume to an exact percentage between 0 and 100.
    Use this when the user says something like 'set volume to 60' or 'volume at 80 percent'."""
    try:
        level = max(0, min(100, level))
        volume = _get_master_volume_interface()
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volume set to {level}%."
    except Exception as e:
        log_error("tool:set_volume", e)
        return f"Failed to set volume: {e}"


@tool
def adjust_volume(direction: str) -> str:
    """Adjusts the system master volume up or down by 10 percentage points.
    'direction' must be either 'up' or 'down'.
    Use this when the user says 'turn up the volume', 'lower the volume', etc."""
    try:
        direction = direction.strip().lower()
        if direction not in ("up", "down"):
            return "Invalid direction. Use 'up' or 'down'."

        volume = _get_master_volume_interface()
        current = round(volume.GetMasterVolumeLevelScalar() * 100)
        step = 10 if direction == "up" else -10
        new_level = max(0, min(100, current + step))
        volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)

        verb = "increased" if direction == "up" else "decreased"
        return f"Volume {verb} to {new_level}%."
    except Exception as e:
        log_error("tool:adjust_volume", e)
        return f"Failed to adjust volume: {e}"


@tool
def mute_unmute_mic() -> str:
    """Toggles the default microphone between muted and unmuted.
    Use this when the user says 'mute my mic', 'unmute microphone', etc."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL

        mic = AudioUtilities.GetMicrophone()
        if mic is None:
            return "No default microphone detected."

        interface = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)

        current_mute = volume.GetMute()
        new_mute = not current_mute
        volume.SetMute(new_mute, None)

        state = "muted" if new_mute else "unmuted"
        return f"Microphone {state}."
    except Exception as e:
        log_error("tool:mute_unmute_mic", e)
        return f"Failed to toggle microphone mute: {e}"


# ---------------------------------------------------------------------------
# Camera privacy toggle (Windows registry — UAC-elevated subprocess)
# ---------------------------------------------------------------------------

_CAMERA_REG_KEY = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion"
    r"\CapabilityAccessManager\ConsentStore\webcam"
)
_CAMERA_REG_PATH_FULL = (
    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion"
    r"\CapabilityAccessManager\ConsentStore\webcam"
)

# ShellExecuteW return codes that indicate the UAC prompt was declined or the
# operation was blocked before the elevated process could start.
_SE_ACCESS_DENIED  = 5   # ERROR_ACCESS_DENIED — UAC declined
_SE_CANCELLED      = 42  # ERROR_CANCELLED — user pressed "No" on UAC dialog


@tool
def mute_unmute_camera() -> str:
    """Toggles the Windows camera privacy setting on or off.
    Reads current state from HKLM (no elevation needed), then writes the new
    value via an elevated reg.exe subprocess triggered by a UAC prompt — so
    only this one action requests admin rights; the rest of the app stays
    unprivileged.
    Use this when the user says 'disable camera', 'block camera access', 'enable camera', etc."""
    import winreg
    import ctypes
    import time

    try:
        # ── 1. Read current state (unprivileged) ──────────────────────────────
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            _CAMERA_REG_KEY,
            0,
            winreg.KEY_READ,
        ) as key:
            current_value, _ = winreg.QueryValueEx(key, "Value")

        new_value = "Deny" if current_value == "Allow" else "Allow"

        # ── 2. Write via ShellExecuteW "runas" (triggers UAC prompt) ──────────
        # reg.exe is a built-in Windows tool; no external dep required.
        reg_cmd = (
            f'add "{_CAMERA_REG_PATH_FULL}"'
            f' /v Value /t REG_SZ /d {new_value} /f'
        )

        # ShellExecuteW returns an HINSTANCE (>32 = success, ≤32 = error code).
        # We call it with nShowCmd=0 (SW_HIDE) so no console window flashes.
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,       # hwnd
            "runas",    # lpVerb — triggers UAC elevation
            "reg.exe",  # lpFile
            reg_cmd,    # lpParameters
            None,       # lpDirectory
            0,          # nShowCmd: SW_HIDE
        )

        if ret in (_SE_ACCESS_DENIED, _SE_CANCELLED):
            return "Camera toggle cancelled — UAC prompt was declined."

        if ret <= 32:
            # Other ShellExecute error codes (e.g. file not found, no assoc)
            return f"Camera toggle failed: ShellExecuteW error code {ret}."

        # ── 3. Wait for reg.exe to finish ────────────────────────────────────
        # ShellExecuteW doesn't give us a process handle, so we poll the
        # registry value until it flips (or time out after ~5 s).
        deadline = time.monotonic() + 5.0
        confirmed = False
        while time.monotonic() < deadline:
            time.sleep(0.15)
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    _CAMERA_REG_KEY,
                    0,
                    winreg.KEY_READ,
                ) as key:
                    actual, _ = winreg.QueryValueEx(key, "Value")
                if actual == new_value:
                    confirmed = True
                    break
            except OSError:
                pass  # key briefly unavailable during write — keep polling

        if not confirmed:
            return (
                "Camera toggle requested but the registry change couldn't be "
                "confirmed in time — UAC may have been dismissed, or the "
                "system took longer than expected."
            )

        state = "disabled (camera access denied)" if new_value == "Deny" else "enabled (camera access allowed)"
        return f"Camera privacy setting updated: camera is now {state}."

    except Exception as e:
        log_error("tool:mute_unmute_camera", e)
        return f"Failed to toggle camera privacy setting: {e}"



# ---------------------------------------------------------------------------
# Brightness controls (screen-brightness-control)
# ---------------------------------------------------------------------------

@tool
def set_brightness(level: int) -> str:
    """Sets the screen brightness to an exact percentage between 0 and 100.
    Use this when the user says 'set brightness to 70' or 'brightness at 50 percent'."""
    try:
        import screen_brightness_control as sbc

        level = max(0, min(100, level))
        sbc.set_brightness(level)
        return f"Brightness set to {level}%."
    except Exception as e:
        log_error("tool:set_brightness", e)
        return f"Failed to set brightness: {e}"


@tool
def adjust_brightness(direction: str) -> str:
    """Adjusts the screen brightness up or down by 10 percentage points.
    'direction' must be either 'up' or 'down'.
    Use this when the user says 'increase brightness', 'dim the screen', etc."""
    try:
        import screen_brightness_control as sbc

        direction = direction.strip().lower()
        if direction not in ("up", "down"):
            return "Invalid direction. Use 'up' or 'down'."

        # get_brightness() returns a list; take the first monitor's value.
        current_levels = sbc.get_brightness()
        current = current_levels[0] if current_levels else 50

        step = 10 if direction == "up" else -10
        new_level = max(0, min(100, current + step))
        sbc.set_brightness(new_level)

        verb = "increased" if direction == "up" else "decreased"
        return f"Brightness {verb} to {new_level}%."
    except Exception as e:
        log_error("tool:adjust_brightness", e)
        return f"Failed to adjust brightness: {e}"

@tool
def take_screenshot() -> str:
    """Captures a full-screen screenshot and saves it to the Pictures\\Screenshots folder.
    Use this when the user says 'take a screenshot', 'capture the screen', etc."""
    try:
        screenshots_dir = r"C:\Users\sithi\Pictures\Screenshots"
        os.makedirs(screenshots_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H%M%S")
        filename = f"Screenshot {timestamp}.png"
        full_path = os.path.join(screenshots_dir, filename)
        
        pyautogui.screenshot(full_path)
        
        return f"Screenshot saved to {full_path}."
    except Exception as e:
        log_error("tool:take_screenshot", str(e))
        return f"Failed to take screenshot: {e}"


# ---------------------------------------------------------------------------
# Power controls
# ---------------------------------------------------------------------------

@tool
def lock_screen() -> str:
    """Locks the Windows screen.
    Use this when the user says 'lock', 'lock it', 'lock my pc', 'lock screen', etc."""
    try:
        # LockWorkStation() is the official Win32 API for locking the workstation.
        # pyautogui.hotkey('win', 'l') is blocked by Windows at the secure-input
        # layer (SendInput cannot synthesise Win+L from an unprivileged process);
        # calling the API directly bypasses that restriction.
        result = ctypes.windll.user32.LockWorkStation()
        if result == 0:
            # Returns 0 on failure (e.g. no interactive desktop)
            err = ctypes.get_last_error()
            return f"Failed to lock screen: LockWorkStation returned 0 (error {err})."
        return "Locked."
    except Exception as e:
        log_error("tool:lock_screen", str(e))
        return f"Failed to lock screen: {e}"

@tool
def request_shutdown() -> str:
    """Call this when Thunder first asks to shut down the computer, before any 
    confirmation has happened. Generates a confirmation code."""
    from app.backend.chat.confirmation import request_confirmation
    token = request_confirmation("shutdown")
    return f"Say the code {token} to confirm shutdown."

@tool
def request_restart() -> str:
    """Call this when Thunder first asks to restart the computer, before any 
    confirmation has happened. Generates a confirmation code."""
    from app.backend.chat.confirmation import request_confirmation
    token = request_confirmation("restart")
    return f"Say the code {token} to confirm restart."

@tool
def shutdown_system(token: str) -> str:
    """Shuts down the computer. Requires the exact numeric confirmation code 
    Thunder was given by request_shutdown. Do not call this directly from a 
    first-time shutdown request — call request_shutdown first."""
    from app.backend.chat.confirmation import check_confirmation
    if not check_confirmation("shutdown", token):
        return "Confirmation failed or expired. Ask again."
    try:
        os.system("shutdown /s /t 0")
        return "Shutting down now."
    except Exception as e:
        log_error("tool:shutdown_system", str(e))
        return f"Failed to shut down system: {e}"

@tool
def restart_system(token: str) -> str:
    """Restarts the computer. Requires the exact numeric confirmation code 
    Thunder was given by request_restart. Do not call this directly from a 
    first-time restart request — call request_restart first."""
    from app.backend.chat.confirmation import check_confirmation
    if not check_confirmation("restart", token):
        return "Confirmation failed or expired. Ask again."
    try:
        os.system("shutdown /r /t 0")
        return "Restarting now."
    except Exception as e:
        log_error("tool:restart_system", str(e))
        return f"Failed to restart system: {e}"