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
