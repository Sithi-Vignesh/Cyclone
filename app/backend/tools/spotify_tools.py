from pywinauto import Application
from pywinauto.findwindows import ElementNotFoundError
import time
from langchain.tools import tool
from app.backend.core.error_logger import log_error

@tool
def spotify_play_song(song_name: str) -> str:
    """Plays a song on Spotify. Use this when the user asks to play a specific song on Spotify. Spotify must be open first."""
    # Wait for Spotify window to load
    for _ in range(30):
        try:
            app = Application(backend="uia").connect(title_re=".*Spotify.*")
            time.sleep(8)  # wait for Spotify UI to fully load
            break
        except ElementNotFoundError:
            time.sleep(0.5)
    else:
        return "Spotify didn't open in time. Try again."

    try:
        window = app.top_window()
        window.set_focus()
        time.sleep(0.5)

        window.type_keys("^l", pause=0.3)
        time.sleep(0.5)

        window.type_keys(song_name, with_spaces=True, pause=0.05)
        time.sleep(0.5)

        window.type_keys("{ENTER}")
        time.sleep(3)

        window.type_keys("{TAB}", pause=0.5)
        window.type_keys("{TAB}", pause=0.5)
        window.type_keys("{DOWN}", pause=0.5)
        window.type_keys("{ENTER}")
    except Exception as e:
        log_error("spotify_play_song", e)
        return "Connected to Spotify but ran into an issue playing that — try again?"

    return f"Playing {song_name} on Spotify."