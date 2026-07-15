"""Unit tests for app/backend/tools/whatsapp_tools.py.

All external dependencies (pywinauto, psutil) are mocked.
No real windows are opened or interactive events triggered.

The key extension point is _find_real_element(), which abstracts all UIA element
lookups.  Tests mock this helper to control which elements exist, isolating
call_contact's control flow from the WebView2 duplication details.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from app.backend.tools.whatsapp_tools import call_contact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_find_elements(contact_name, should_find=True):
    """Return a side_effect for findwindows.find_elements that simulates headers."""
    def side_effect(**kwargs):
        if kwargs.get("control_type") == "DataItem":
            header1 = MagicMock()
            header1.name = "Chats"
            header1.class_name = "Header"
            header2 = MagicMock()
            header2.name = "Groups in common"
            header2.class_name = "Header"
            
            if not should_find:
                return [header1, header2]
                
            contact = MagicMock()
            contact.name = contact_name
            contact.class_name = "Contact"
            return [header1, header2, contact]
        return []
    return side_effect

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
            ("Search or start a new chat", "Edit"): search_box_mock,
            (None, "DataItem"): contact_mock,
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


def test_search_box_not_found():
    """If _find_real_element returns None for the search box, return an error."""
    app_mock, window_mock = _make_app_and_window()

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element", return_value=None),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice")
        assert "Could not find the WhatsApp search box" in result


def test_contact_not_found():
    """If the DataItem never appears, return a contact-not-found message."""
    app_mock, window_mock = _make_app_and_window()

    search_box_mock = MagicMock()
    mapping = {
        ("Search or start a new chat", "Edit"): search_box_mock,
        ("Voice call", "Button"): None,
    }

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element",
              side_effect=_mock_find_real_element(mapping)),
        patch("app.backend.tools.whatsapp_tools.findwindows.find_elements",
              side_effect=_mock_find_elements("Alice", should_find=False)),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice")
        assert "Couldn't find that contact" in result


def test_call_button_not_found():
    """Contact found but call button absent → appropriate error message."""
    app_mock, window_mock = _make_app_and_window()

    search_box_mock = MagicMock()
    contact_mock = MagicMock()
    mapping = {
        ("Search or start a new chat", "Edit"): search_box_mock,
        ("Alice", "DataItem"): contact_mock,
        ("Voice call", "Button"): None,   # button absent
    }

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element",
              side_effect=_mock_find_real_element(mapping)),
        patch("app.backend.tools.whatsapp_tools.findwindows.find_elements",
              side_effect=_mock_find_elements("Alice", should_find=True)),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice")
        assert "Could not find the voice call button" in result


def test_voice_call_success():
    """Full happy-path voice call — verify return value and interaction sequence."""
    app_mock, window_mock = _make_app_and_window()

    search_box_mock = MagicMock()
    contact_mock = MagicMock()
    call_btn_mock = MagicMock()
    mapping = {
        ("Search or start a new chat", "Edit"): search_box_mock,
        ("Alice", "DataItem"): contact_mock,
        ("Voice call", "Button"): call_btn_mock,
    }

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element",
              side_effect=_mock_find_real_element(mapping)) as mock_fre,
        patch("app.backend.tools.whatsapp_tools.findwindows.find_elements",
              side_effect=_mock_find_elements("Alice", should_find=True)),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice", video=False)

    assert "Placed a WhatsApp voice call to Alice" in result

    # Verify _find_real_element was called for all three element types
    mock_fre.assert_any_call(
        window_mock,
        title="Search or start a new chat",
        control_type="Edit",
        timeout=5,
    )
    mock_fre.assert_any_call(
        window_mock,
        title="Alice",
        control_type="DataItem",
        timeout=0,
    )
    mock_fre.assert_any_call(
        window_mock,
        title="Voice call",
        control_type="Button",
        timeout=10,
    )

    # Verify all three elements were clicked
    search_box_mock.click_input.assert_called_once()
    contact_mock.click_input.assert_called_once()
    call_btn_mock.click_input.assert_called_once()

    # Verify text-entry sequence
    window_mock.type_keys.assert_any_call("^a{BACKSPACE}", pause=0.1)
    window_mock.type_keys.assert_any_call("Alice", with_spaces=True, pause=0.05)


def test_video_call_success():
    """Full happy-path video call — verify Video call button is requested."""
    app_mock, window_mock = _make_app_and_window()

    search_box_mock = MagicMock()
    contact_mock = MagicMock()
    call_btn_mock = MagicMock()
    mapping = {
        ("Search or start a new chat", "Edit"): search_box_mock,
        ("Alice", "DataItem"): contact_mock,
        ("Video call", "Button"): call_btn_mock,
    }

    with (
        patch("app.backend.tools.whatsapp_tools._connect_whatsapp_window", return_value=app_mock),
        patch("app.backend.tools.whatsapp_tools._find_real_element",
              side_effect=_mock_find_real_element(mapping)) as mock_fre,
        patch("app.backend.tools.whatsapp_tools.findwindows.find_elements",
              side_effect=_mock_find_elements("Alice", should_find=True)),
        patch("app.backend.tools.whatsapp_tools.time.sleep"),
    ):
        result = call_contact("Alice", video=True)

    assert "Placed a WhatsApp video call to Alice" in result
    mock_fre.assert_any_call(
        window_mock,
        title="Video call",
        control_type="Button",
        timeout=10,
    )
    call_btn_mock.click_input.assert_called_once()
