import time
from pywinauto import Application, findwindows
from langchain.tools import tool
from app.backend.core.error_logger import log_error
from app.backend.tools.system_tools import open_application
import psutil


def _connect_whatsapp_window(max_wait_ticks: int = 30, tick_interval: float = 0.5):
    """Connect to the WhatsApp window by process name, retrying while it launches.
    Returns the pywinauto Application on success, None on timeout."""
    for _ in range(max_wait_ticks):
        try:
            for w in findwindows.find_elements(backend="uia", visible_only=False):
                try:
                    proc = psutil.Process(w.process_id)
                    if "whatsapp" in proc.name().lower():
                        return Application(backend="uia").connect(process=w.process_id)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        time.sleep(tick_interval)
    return None


def _find_real_element(window, title=None, control_type=None, timeout=10.0):
    """Find an interactable UIA element inside the WhatsApp WebView2 window,
    working around the WebView2 UIA duplication bug.

    Background — the WebView2 UIA duplication bug:
      WhatsApp Desktop is built on Electron/WebView2, which exposes its DOM
      accessibility tree through UIA.  Chromium's UIA bridge replicates every
      named accessibility node ~79 times in the tree: one real node plus ~78
      phantom shadow copies.  All copies share identical title, control_type,
      rectangle, is_visible, and is_enabled values — they cannot be told apart
      by any single UIA property.

      Clicking through any of the 79 wrapper handles sends the interaction to
      the same on-screen coordinates, so index 0 is a correct and stable choice.

      Using pywinauto's plain child_window(title=...) raises ElementAmbiguousError
      when more than one match exists.  The fix is to always pass found_index=0
      so pywinauto selects the first candidate without raising.

    Strategy:
      Build a child_window descriptor with found_index=0 (and the caller-supplied
      title / control_type filters), then poll .exists() with bounded retries until
      the element appears or the timeout elapses.

    Args:
        window:        The pywinauto top_window() wrapper for the WhatsApp window.
        title:         UIA name / accessibility title of the element, or None to
                       match any title.
        control_type:  UIA control type string (e.g. "Button", "Edit"),
                       or None to skip that filter.
        timeout:       Maximum seconds to poll before giving up.

    Returns:
        A pywinauto WindowSpecification (interactable) for the first found element,
        or None if no match is confirmed within the timeout.
    """
    deadline = time.time() + timeout

    # Build keyword args for child_window — only include filters that were supplied.
    # found_index=0 is always passed so pywinauto never raises ElementAmbiguousError
    # even when WebView2 has replicated the node 79 times in the UIA tree.
    spec_kwargs = {"found_index": 0}
    if title is not None:
        spec_kwargs["title"] = title
    if control_type is not None:
        spec_kwargs["control_type"] = control_type

    while True:
        try:
            elem = window.child_window(**spec_kwargs)
            if elem.exists(timeout=0.3):
                return elem
        except Exception:
            pass

        if time.time() >= deadline:
            return None
        time.sleep(0.25)


@tool
def call_contact(name: str, video: bool = False) -> str:
    """Places a WhatsApp voice or video call to a contact or group by name.
    Use this when the user asks to call someone on WhatsApp."""
    try:
        already_open = False
        app = _connect_whatsapp_window(max_wait_ticks=1, tick_interval=0)
        if app is not None:
            already_open = True
        else:
            if hasattr(open_application, "invoke"):
                open_application.invoke({"app_name": "whatsapp"})
            else:
                open_application("whatsapp")
            time.sleep(7)  # cold start: give WhatsApp's Electron UI time to fully render
            app = _connect_whatsapp_window(max_wait_ticks=10, tick_interval=0.5)

        if app is None:
            return "WhatsApp didn't open in time. Try again."

        window = app.top_window()
        window.set_focus()
        time.sleep(2.5 if already_open else 1)  # already-open needs a beat to raise/focus

        # --- Step 1: focus the search bar via WhatsApp's native shortcut ---
        # Ctrl+F is WhatsApp Desktop's keyboard shortcut for "focus search".
        # It works reliably from any UI state (home, chat open, search already
        # active) without needing a UIA element lookup, so it sidesteps all
        # leftover-state and WebView2-duplication issues from previous calls.
        window.type_keys("^f")
        time.sleep(0.4)  # let the focus animation settle

        # Clear any text left over from a previous call, then type the new name.
        window.type_keys("^a{BACKSPACE}", pause=0.1)
        time.sleep(0.3)

        # --- Step 2: type the contact name ---
        window.type_keys(name, with_spaces=True, pause=0.05)
        time.sleep(1.2)  # give search results time to populate

        # --- Step 3: open the top result with Enter ---
        # Enter navigates directly into the first search result's chat, removing
        # the need for DataItem UIA enumeration entirely.
        window.type_keys("{ENTER}")
        time.sleep(1.2)  # let the chat view fully load before looking for the call button

        # --- Step 4: locate and click the call button ---
        button_name = "Video call" if video else "Voice call"
        call_btn = _find_real_element(
            window,
            title=button_name,
            control_type="Button",
            timeout=2,
        )
        if call_btn is None:
            return (
                f"Could not find the {button_name.lower()} button for {name}. "
                "The UI might not have loaded or the option is unavailable."
            )

        call_btn.click_input()

        call_type = "video call" if video else "voice call"
        return f"Placed a WhatsApp {call_type} to {name}."

    except Exception as e:
        log_error("tool:call_contact", e)
        return f"Failed to call {name} on WhatsApp: {e}"


@tool
def text_contact(name: str, message: str) -> str:
    """Types a WhatsApp message to a contact or group by name and leaves it
    ready to send. The message is NOT sent automatically — the user sends it
    manually by pressing Enter.
    Use this when the user asks to text, message, or write to someone on WhatsApp."""
    try:
        already_open = False
        app = _connect_whatsapp_window(max_wait_ticks=1, tick_interval=0)
        if app is not None:
            already_open = True
        else:
            if hasattr(open_application, "invoke"):
                open_application.invoke({"app_name": "whatsapp"})
            else:
                open_application("whatsapp")
            time.sleep(7)  # cold start: give WhatsApp's Electron UI time to fully render
            app = _connect_whatsapp_window(max_wait_ticks=10, tick_interval=0.5)

        if app is None:
            return "WhatsApp didn't open in time. Try again."

        window = app.top_window()
        window.set_focus()
        time.sleep(2.5 if already_open else 1)  # already-open needs a beat to raise/focus

        # --- Step 1: focus the search bar via WhatsApp's native shortcut ---
        window.type_keys("^f")
        time.sleep(0.4)  # let the focus animation settle

        # --- Step 2: clear any leftover text from a previous search ---
        window.type_keys("^a{BACKSPACE}", pause=0.1)
        time.sleep(0.3)

        # --- Step 3: type the contact name ---
        window.type_keys(name, with_spaces=True, pause=0.05)
        time.sleep(1.2)  # give search results time to populate

        # --- Step 4: open the top result — cursor auto-lands on the message bar ---
        # Enter navigates into the first search result's chat.  WhatsApp Desktop
        # automatically focuses the message input box after navigation, so no
        # additional click or UIA element lookup is required.
        window.type_keys("{ENTER}")
        time.sleep(1.0)  # let the chat view load and the input box gain focus

        # --- Step 5: type the message (do NOT send — user sends manually) ---
        window.type_keys(message, with_spaces=True, pause=0.05)

        return (
            f"Typed your message to {name} on WhatsApp. "
            "Press Enter (or click Send) whenever you're ready."
        )

    except Exception as e:
        log_error("tool:text_contact", e)
        return f"Failed to text {name} on WhatsApp: {e}"
