from langchain.tools import tool
import os
import subprocess

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