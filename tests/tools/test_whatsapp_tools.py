"""Unit tests for app/backend/tools/whatsapp_tools.py.

All external dependencies (pywinauto, psutil) are mocked.
No real windows are opened or interactive events triggered.

The search flow now uses WhatsApp's native keyboard shortcuts (Ctrl+F → clear →
type → Enter) instead of UIA element lookups, so tests assert on window.type_keys
call sequences rather than _find_real_element / DataItem tree interactions.
_find_real_element is still used for the call button lookup and is mocked there.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from app.backend.tools.whatsapp_tools import call_contact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app_and_window():
    """Return a (app_mock, window_mock) pair wired together."""
    app_mock = MagicMock()
    window_mock = MagicMock()
    app_mock.top_window.return_value = window_mock
    return app_mock, window_mock


def _mock_find_real_element(mapping):
    """Return a side_effect function for _find_real_element.

    'mapping' is a dict keyed by (title, control_type) tuples.  Return values
    are the mocked element, or None if the key is absent.

    Example:
        mapping = {
            ("Voice call", "Button"): call_btn_mock,
        }
    """
    def side_effect(window, title=None, control_type=None, timeout=10.0):
        return mapping.get((title, control_type))
    return side_effect


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_whatsapp_not_running():
    """If WhatsApp doesn't open in time, a friendly message is returned."""
    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=None),
        patch("app.backend.tools.whatsapp_tools.open_application"),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice")
        assert "WhatsApp didn't open in time" in result


def test_call_button_not_found():
    """Contact navigated to but call button absent → appropriate error message."""
    app_mock, window_mock = _make_app_and_window()

    mapping = {
        ("Voice call", "Button"): None,  # button absent
    }

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element",
              side_effect=_mock_find_real_element(mapping)),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice")
        assert "Could not find the voice call button" in result


def test_voice_call_success():
    """Full happy-path voice call — verify return value and interaction sequence."""
    app_mock, window_mock = _make_app_and_window()

    call_btn_mock = MagicMock()
    mapping = {
        ("Voice call", "Button"): call_btn_mock,
    }

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element",
              side_effect=_mock_find_real_element(mapping)) as mock_fre,
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice", video=False)

    assert "Placed a WhatsApp voice call to Alice" in result

    # Verify _find_real_element was called only for the call button (not search box)
    mock_fre.assert_called_once_with(
        window_mock,
        title="Voice call",
        control_type="Button",
        timeout=2,
    )

    # Verify the keyboard-shortcut search sequence
    type_keys_calls = window_mock.type_keys.call_args_list
    keys_sent = [c.args[0] if c.args else c.kwargs.get("keys") for c in type_keys_calls]
    assert "^f" in keys_sent, "Ctrl+F to focus search not sent"
    assert "{ENTER}" in keys_sent, "Enter to open top result not sent"

    # Verify clear and name-type calls are present
    window_mock.type_keys.assert_any_call("^a{BACKSPACE}", pause=0.1)
    window_mock.type_keys.assert_any_call("Alice", with_spaces=True, pause=0.05)

    # Ctrl+F must come before the contact name
    idx_ctrlf = next(i for i, c in enumerate(type_keys_calls) if c.args and c.args[0] == "^f")
    idx_name  = next(i for i, c in enumerate(type_keys_calls)
                     if c.kwargs.get("with_spaces") and c.args and c.args[0] == "Alice")
    assert idx_ctrlf < idx_name, "^f must be sent before the contact name"

    # Enter must come after the contact name
    idx_enter = next(i for i, c in enumerate(type_keys_calls) if c.args and c.args[0] == "{ENTER}")
    assert idx_name < idx_enter, "Contact name must be typed before Enter"

    # Call button clicked exactly once
    call_btn_mock.click_input.assert_called_once()


def test_video_call_success():
    """Full happy-path video call — verify Video call button is requested."""
    app_mock, window_mock = _make_app_and_window()

    call_btn_mock = MagicMock()
    mapping = {
        ("Video call", "Button"): call_btn_mock,
    }

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element",
              side_effect=_mock_find_real_element(mapping)) as mock_fre,
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice", video=True)

    assert "Placed a WhatsApp video call to Alice" in result
    mock_fre.assert_called_once_with(
        window_mock,
        title="Video call",
        control_type="Button",
        timeout=2,
    )
    call_btn_mock.click_input.assert_called_once()


def test_keyboard_shortcut_order():
    """Verify Ctrl+F → clear → name → Enter order is always respected."""
    app_mock, window_mock = _make_app_and_window()

    call_btn_mock = MagicMock()
    mapping = {("Voice call", "Button"): call_btn_mock}

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element",
              side_effect=_mock_find_real_element(mapping)),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        call_contact("Bob", video=False)

    calls = window_mock.type_keys.call_args_list

    def idx(key):
        for i, c in enumerate(calls):
            arg = c.args[0] if c.args else None
            if arg == key:
                return i
        return None

    assert idx("^f") is not None,           "^f not sent"
    assert idx("{ENTER}") is not None,      "{ENTER} not sent"
    assert idx("^f") < idx("{ENTER}"),      "^f must precede {ENTER}"


# ---------------------------------------------------------------------------
# text_contact tests
# ---------------------------------------------------------------------------

from app.backend.tools.whatsapp_tools import text_contact  # noqa: E402


def test_text_contact_whatsapp_not_running():
    """If WhatsApp doesn't open in time, a friendly error is returned."""
    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=None),
        patch("app.backend.tools.whatsapp_tools.open_application"),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = text_contact("Alice", "Hey, how are you?")
        assert "WhatsApp didn't open in time" in result


def test_text_contact_success():
    """Full happy-path: correct key sequence and no call-button lookup."""
    app_mock, window_mock = _make_app_and_window()

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element") as mock_fre,
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = text_contact("Alice", "Hey, how are you?")

    # _find_real_element must never be called — no call-button lookup in text_contact
    mock_fre.assert_not_called()

    assert "Typed your message to Alice" in result

    type_keys_calls = window_mock.type_keys.call_args_list
    keys_sent = [c.args[0] if c.args else c.kwargs.get("keys") for c in type_keys_calls]

    # Required keystrokes present
    assert "^f" in keys_sent,          "Ctrl+F (open search) not sent"
    assert "{ENTER}" in keys_sent,     "Enter (open chat) not sent"

    # Clear and name typing present
    window_mock.type_keys.assert_any_call("^a{BACKSPACE}", pause=0.1)
    window_mock.type_keys.assert_any_call("Alice", with_spaces=True, pause=0.05)

    # Message typing present
    window_mock.type_keys.assert_any_call("Hey, how are you?", with_spaces=True, pause=0.05)

    # Enter must NOT be the final type_keys call — message comes after it
    idx_enter = next(i for i, c in enumerate(type_keys_calls) if c.args and c.args[0] == "{ENTER}")
    idx_msg   = next(
        i for i, c in enumerate(type_keys_calls)
        if c.args and c.args[0] == "Hey, how are you?"
    )
    assert idx_enter < idx_msg, "Enter (open chat) must precede the message text"


def test_text_contact_no_extra_enter():
    """Verify Enter is sent exactly once (to open the chat) and never after the message."""
    app_mock, window_mock = _make_app_and_window()

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element"),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        text_contact("Bob", "Call me later")

    type_keys_calls = window_mock.type_keys.call_args_list
    enter_calls = [c for c in type_keys_calls if c.args and c.args[0] == "{ENTER}"]
    assert len(enter_calls) == 1, "Enter must be sent exactly once (chat open), not after message"

    # The message must be the last type_keys call
    last_call = type_keys_calls[-1]
    assert last_call.args[0] == "Call me later", "Message must be the last type_keys call"


def test_text_contact_keyboard_order():
    """Strict ordering: ^f → clear → name → {ENTER} → message."""
    app_mock, window_mock = _make_app_and_window()

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element"),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        text_contact("Charlie", "See you soon")

    calls = window_mock.type_keys.call_args_list

    def idx(key):
        for i, c in enumerate(calls):
            if c.args and c.args[0] == key:
                return i
        return None

    def idx_kwarg(key_value):
        """Find a call whose first arg equals key_value (used for with_spaces calls)."""
        for i, c in enumerate(calls):
            if c.args and c.args[0] == key_value:
                return i
        return None

    i_ctrlf  = idx("^f")
    i_clear  = idx("^a{BACKSPACE}")
    i_name   = idx_kwarg("Charlie")
    i_enter  = idx("{ENTER}")
    i_msg    = idx_kwarg("See you soon")

    assert i_ctrlf  is not None, "^f not sent"
    assert i_clear  is not None, "^a{BACKSPACE} not sent"
    assert i_name   is not None, "Contact name not typed"
    assert i_enter  is not None, "{ENTER} not sent"
    assert i_msg    is not None, "Message not typed"

    assert i_ctrlf < i_clear,  "^f must precede clear"
    assert i_clear < i_name,   "clear must precede contact name"
    assert i_name  < i_enter,  "contact name must precede Enter"
    assert i_enter < i_msg,    "Enter must precede message text"

