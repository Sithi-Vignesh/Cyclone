from langchain.tools import tool
import os
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