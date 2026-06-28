from langchain.tools import tool
import os
import subprocess
import psutil
import pyperclip

@tool
def open_application(app_name: str) -> str:
    """Opens an application on the system by name. Use this when the user asks to open an app like VS Code, Chrome, Notepad, etc."""
    try:
        subprocess.Popen(app_name)
        return f"Opened {app_name} successfully."
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
    battery = psutil.sensors_battery()
    if battery is None:
        return "Battery info not available."
    status = "charging" if battery.power_plugged else "not charging"
    return f"Battery is at {battery.percent:.0f}%, {status}."

@tool
def read_clipboard() -> str:
    """Reads and returns the current text content from the clipboard."""
    import pyperclip
    text = pyperclip.paste()
    if not text:
        return "Clipboard is empty."
    return f"Clipboard contents: {text}"