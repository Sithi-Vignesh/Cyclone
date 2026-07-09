"""Window management tools for Cyclone.

Architecture:
- Named-window actions (minimize/maximize/close/focus a specific app)
  → pywinauto: we call findwindows.find_element() directly to locate the
    target process, then wrap it with Application(backend="uia").connect()
    via process ID.  We do NOT pass title_re to Application.connect() because
    of a pywinauto bug: any call with `timeout` in kwargs (including timeout=0)
    is routed through wait_until_passes() using the *default* 5-second
    Timings.app_connect_timeout rather than the caller-supplied value — and on
    failure it raises TimeoutError() (no message), not ElementNotFoundError,
    so the empty string in `f"...: {e}"` is the result.
- Global / desktop-wide actions (no target app given)
  → pyautogui.hotkey() sending the native Windows keyboard shortcut.
- pygetwindow stays read-only: used only to resolve the active window title
  when the caller omits app_name (mirrors get_active_window in system_tools).
"""

import re
import time

import pyautogui
import pygetwindow as gw
from langchain.tools import tool
from pywinauto import Application
from pywinauto import findwindows
from pywinauto.findwindows import ElementNotFoundError

from app.backend.core.error_logger import log_error

# How many 0.25-second ticks to wait when searching for a named window.
# 5 ticks = 1.25 s maximum wait — short enough to feel snappy, long enough
# to handle a window that's in the middle of being raised.
_CONNECT_RETRIES = 5
_CONNECT_INTERVAL = 0.25


def _connect_by_title(app_name: str):
    """Try to connect to a window whose title partially matches *app_name*.

    Performs up to _CONNECT_RETRIES attempts with _CONNECT_INTERVAL spacing.
    Returns an ``Application`` instance on success, ``None`` on timeout.

    The title regex is ``.*<escaped app_name>.*`` so that "chrome" matches
    "Google Chrome - New Tab", etc.

    We call findwindows.find_element() directly instead of
    Application.connect(title_re=..., timeout=0) because of a pywinauto bug:
    passing any `timeout` kwarg to connect() routes execution through
    wait_until_passes() with the *default* Timings.app_connect_timeout (5 s),
    not the caller-supplied value.  On failure it raises TimeoutError() with
    no message string — so f"...: {e}" produces an empty suffix.  Going
    directly to find_element() gives us one synchronous attempt per tick and
    raises ElementNotFoundError (with the search kwargs as its message) which
    we handle cleanly.
    """
    # (?i) is the inline flag for re.IGNORECASE
    pattern = f"(?i).*{re.escape(app_name)}.*"
    for _ in range(_CONNECT_RETRIES):
        try:
            elem = findwindows.find_element(
                title_re=pattern,
                backend="uia",
                visible_only=False,
            )
            return Application(backend="uia").connect(process=elem.process_id)
        except ElementNotFoundError:
            time.sleep(_CONNECT_INTERVAL)
    return None


def _active_window_title() -> str | None:
    """Return the title of the currently active window, or None."""
    win = gw.getActiveWindow()
    return win.title if win is not None else None


# ---------------------------------------------------------------------------
# minimize_window
# ---------------------------------------------------------------------------

@tool
def minimize_window(app_name: str = "") -> str:
    """Minimizes a window by app name, or shows the desktop if no app is specified.
    If app_name is empty, minimizes all windows (Win + D shortcut).
    If app_name is given, minimizes that specific window by partial title match.
    Use this when the user says 'minimize Chrome', 'minimize everything', 'show desktop', etc."""
    try:
        if not app_name.strip():
            pyautogui.hotkey("win", "d")
            return "Minimized all windows."

        app = _connect_by_title(app_name)
        if app is None:
            return f"Couldn't find a window matching '{app_name}'."

        app.top_window().minimize()
        return f"Minimized {app_name}."

    except Exception as e:
        log_error("tool:minimize_window", e)
        return f"Failed to minimize '{app_name}': {e}"


# ---------------------------------------------------------------------------
# maximize_window
# ---------------------------------------------------------------------------

@tool
def maximize_window(app_name: str = "") -> str:
    """Maximizes a window by app name, or maximizes the currently active window if no name is given.
    Use this when the user says 'maximize Chrome', 'make this window fullscreen', 'maximize the current window', etc."""
    try:
        if not app_name.strip():
            title = _active_window_title()
            if not title:
                return "No active window detected to maximize."
            app = _connect_by_title(title)
            if app is None:
                return "Couldn't connect to the active window to maximize it."
            app.top_window().maximize()
            return "Maximized the active window."

        app = _connect_by_title(app_name)
        if app is None:
            return f"Couldn't find a window matching '{app_name}'."

        app.top_window().maximize()
        return f"Maximized {app_name}."

    except Exception as e:
        log_error("tool:maximize_window", e)
        return f"Failed to maximize '{app_name}': {e}"


# ---------------------------------------------------------------------------
# close_window
# ---------------------------------------------------------------------------

@tool
def close_window(app_name: str = "") -> str:
    """Closes a window by app name, or closes the currently active window if no name is given.
    Use this when the user says 'close Chrome', 'close this window', 'close the active app', etc."""
    try:
        if not app_name.strip():
            title = _active_window_title()
            if not title:
                return "No active window detected to close."
            app = _connect_by_title(title)
            if app is None:
                return "Couldn't connect to the active window to close it."
            app.top_window().close()
            return "Closed the active window."

        app = _connect_by_title(app_name)
        if app is None:
            return f"Couldn't find a window matching '{app_name}'."

        app.top_window().close()
        return f"Closed {app_name}."

    except Exception as e:
        log_error("tool:close_window", e)
        return f"Failed to close '{app_name}': {e}"


# ---------------------------------------------------------------------------
# focus_window
# ---------------------------------------------------------------------------

@tool
def focus_window(app_name: str) -> str:
    """Brings a specific window to the foreground by app name.
    app_name is required — focusing nothing is meaningless.
    Use this when the user says 'switch to Chrome', 'bring up VS Code', 'focus Notepad', etc."""
    try:
        if not app_name.strip():
            return "Which app do you want me to focus?"

        app = _connect_by_title(app_name)
        if app is None:
            return f"Couldn't find a window matching '{app_name}'."

        app.top_window().set_focus()
        return f"Switched focus to {app_name}."

    except Exception as e:
        log_error("tool:focus_window", e)
        return f"Failed to focus '{app_name}': {e}"
