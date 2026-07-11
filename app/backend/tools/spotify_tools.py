import ctypes
from pywinauto import Application, findwindows
from pywinauto.findwindows import ElementNotFoundError
import time
from langchain.tools import tool
from app.backend.core.error_logger import log_error
from app.backend.tools.system_tools import open_application
import psutil

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3

def _send_media_key(vk_code: int):
    """Send a global media key via Windows keybd_event. Works regardless of
    which window has focus, and does not require Spotify's window to exist —
    routes through the OS's System Media Transport Controls to whatever app
    currently owns the active media session."""
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)       # key down
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)       # key up (KEYEVENTF_KEYUP=2)

def _connect_spotify_window(max_wait_ticks: int = 30, tick_interval: float = 0.5):
    """Connect to the Spotify window by process name, retrying while it launches.
    Matches on process (Spotify.exe) rather than window title, since Spotify's
    title changes to the current song name during playback and stops containing
    the literal word 'Spotify'. Returns the pywinauto Application on success,
    None on timeout."""
    for _ in range(max_wait_ticks):
        try:
            # Filter candidates by process name matching Spotify.exe
            for w in findwindows.find_elements(backend="uia", visible_only=False):
                try:
                    proc = psutil.Process(w.process_id)
                    if proc.name().lower() == "spotify.exe":
                        return Application(backend="uia").connect(process=w.process_id)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        time.sleep(tick_interval)
    return None

@tool
def spotify_play_song(song_name: str) -> str:
    """Plays a song on Spotify by name. Opens Spotify first if it isn't already running.
    Use this when the user asks to play a specific song."""
    try:
        already_open = False
        app = _connect_spotify_window(max_wait_ticks=1, tick_interval=0)
        if app is not None:
            already_open = True
        else:
            if hasattr(open_application, "invoke"):
                open_application.invoke({"app_name": "spotify"})
            else:
                open_application("spotify")
            time.sleep(7)  # cold start: give Spotify's Electron UI time to fully render
            app = _connect_spotify_window(max_wait_ticks=10, tick_interval=0.5)
            
        if app is None:
            return "Spotify didn't open in time. Try again."

        window = app.top_window()
        window.set_focus()
        time.sleep(2.5 if already_open else 1)  # already-open still needs a beat to raise/focus; cold-start already waited during launch

        window.type_keys("^k", pause=0.3)
        time.sleep(0.5)
        window.type_keys(song_name, with_spaces=True, pause=0.05)
        time.sleep(2.5)
        window.type_keys("+{ENTER}")
        window.type_keys("{ESC}")

        return f"Playing {song_name} on Spotify."
    except Exception as e:
        log_error("tool:spotify_play_song", e)
        return f"Failed to play '{song_name}': {e}"

@tool
def spotify_play_pause() -> str:
    """Toggles play/pause for whatever is currently playing (Spotify or otherwise).
    Works even if Spotify is minimized or backgrounded."""
    try:
        _send_media_key(VK_MEDIA_PLAY_PAUSE)
        return "Toggled play/pause."
    except Exception as e:
        log_error("tool:spotify_play_pause", e)
        return f"Failed to toggle play/pause: {e}"

@tool
def spotify_next_track() -> str:
    """Skips to the next track. Works even if Spotify is minimized or backgrounded."""
    try:
        _send_media_key(VK_MEDIA_NEXT_TRACK)
        return "Skipped to next track."
    except Exception as e:
        log_error("tool:spotify_next_track", e)
        return f"Failed to skip track: {e}"

@tool
def spotify_previous_track() -> str:
    """Goes to the previous track. Works even if Spotify is minimized or backgrounded."""
    try:
        _send_media_key(VK_MEDIA_PREV_TRACK)
        return "Went to previous track."
    except Exception as e:
        log_error("tool:spotify_previous_track", e)
        return f"Failed to go to previous track: {e}"

@tool
def spotify_toggle_shuffle() -> str:
    """Toggles shuffle mode on Spotify."""
    try:
        app = _connect_spotify_window()
        if app is None:
            return "Spotify didn't open in time. Try again."
        window = app.top_window()
        window.set_focus()
        time.sleep(0.5)
        window.type_keys("^s")
        return "Toggled shuffle on Spotify."
    except Exception as e:
        log_error("tool:spotify_toggle_shuffle", e)
        return f"Failed to toggle shuffle: {e}"

@tool
def spotify_toggle_repeat() -> str:
    """Toggles repeat mode on Spotify."""
    try:
        app = _connect_spotify_window()
        if app is None:
            return "Spotify didn't open in time. Try again."
        window = app.top_window()
        window.set_focus()
        time.sleep(0.5)
        window.type_keys("^r")
        return "Toggled repeat mode on Spotify."
    except Exception as e:
        log_error("tool:spotify_toggle_repeat", e)
        return f"Failed to toggle repeat: {e}"

@tool
def spotify_like_current_song() -> str:
    """Likes the current song on Spotify."""
    try:
        app = _connect_spotify_window()
        if app is None:
            return "Spotify didn't open in time. Try again."
        window = app.top_window()
        window.set_focus()
        time.sleep(0.5)
        window.type_keys("%+b")
        return "Liked the current song."
    except Exception as e:
        log_error("tool:spotify_like_current_song", e)
        return f"Failed to like current song: {e}"

@tool
def spotify_play_liked_songs() -> str:
    """Plays the Liked Songs playlist on Spotify."""
    try:
        app = _connect_spotify_window()
        if app is None:
            return "Spotify didn't open in time. Try again."
        window = app.top_window()
        window.set_focus()
        time.sleep(0.5)
        window.type_keys("%+s")
        time.sleep(0.5)
        window.type_keys("{TAB}")
        window.type_keys("{TAB}")
        window.type_keys("{ENTER}")
        return "Playing your Liked Songs playlist."
    except Exception as e:
        log_error("tool:spotify_play_liked_songs", e)
        return f"Failed to play liked songs: {e}"