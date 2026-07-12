import os
import difflib
import subprocess
from langchain.tools import tool
from app.backend.core.error_logger import log_error

INDEX_PARENTS = [
    r"C:\Users\sithi\Coding",
    r"C:\Users\sithi\Documents",
    r"C:\Users\sithi\Documents\Personal",
    r"C:\Users\sithi\Pictures",
    r"C:\Users\sithi\Desktop",
]

_folder_index: dict[str, list[str]] = {}

def build_folder_index() -> dict[str, list[str]]:
    """Walk each parent in INDEX_PARENTS one level deep (non-recursive),
    collecting immediate subfolder names. Names are stored lowercase as
    keys; each key maps to a LIST of full paths.
    """
    global _folder_index
    _folder_index.clear()
    
    for parent in INDEX_PARENTS:
        parent_name = os.path.basename(parent).lower()
        _folder_index.setdefault(parent_name, []).append(parent)
        
        try:
            for item in os.listdir(parent):
                item_path = os.path.join(parent, item)
                if os.path.isdir(item_path):
                    item_name = item.lower()
                    _folder_index.setdefault(item_name, []).append(item_path)
        except Exception as e:
            log_error(f"build_folder_index: failed to read {parent}", str(e))
            
    # Also add fixed OS-standard aliases not already covered
    downloads_path = r"C:\Users\sithi\Downloads"
    _folder_index.setdefault("downloads", []).append(downloads_path)
    
    print(f"Built folder index with {len(_folder_index)} entries.")
    return _folder_index

# Call once when module is imported
build_folder_index()

def _resolve_folder(spoken_name: str) -> tuple[str | None, list[str]]:
    """Look up spoken_name against the pre-built _folder_index.
    Returns (resolved_path, []) on a clean single match,
    (None, [list of candidate paths]) if multiple matches collide,
    (None, []) if nothing matches at all.
    """
    normalized_spoken = spoken_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    # Normalize index keys similarly just for matching
    normalized_keys = {k.replace(" ", "").replace("-", "").replace("_", ""): k for k in _folder_index.keys()}
    
    matches = difflib.get_close_matches(normalized_spoken, list(normalized_keys.keys()), n=1, cutoff=0.5)
    
    if not matches:
        return None, []
        
    best_normalized_key = matches[0]
    best_actual_key = normalized_keys[best_normalized_key]
    
    candidates = _folder_index[best_actual_key]
    
    if len(candidates) == 1:
        return candidates[0], []
    else:
        return None, candidates

@tool
def open_folder(folder_name: str, app: str = "explorer") -> str:
    """Opens a folder by name in File Explorer or VS Code. Searches a
    pre-built index covering Coding, Documents, Documents/Personal,
    Pictures, Desktop, and Downloads. Use this when the user says
    'open X folder', 'open project X', 'open project X in vscode', etc.
    app defaults to 'explorer'; pass 'code' for VS Code."""
    try:
        resolved_path, candidates = _resolve_folder(folder_name)
        
        if resolved_path:
            subprocess.Popen(f'{app} "{resolved_path}"', shell=True)
            return f"Opened {resolved_path} in {app}."
        elif candidates:
            return f"Found '{folder_name}' in multiple places: {', '.join(candidates)}. Which one did you mean?"
        else:
            return f"Couldn't find a folder matching '{folder_name}'."
    except Exception as e:
        log_error("tool:open_folder", str(e))
        return f"An error occurred while opening the folder: {str(e)}"
