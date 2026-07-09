"""tests/tools/conftest.py

Pre-stub truly-external / non-installable modules before any tool module is
imported during pytest collection.  This ensures no real system calls, network
calls, or external processes are started at import time.

IMPORTANT: We do NOT stub any app.backend.* modules here.  The existing
tests/conftest.py already stubs the ones that need it for the full suite.
Individual tool tests use unittest.mock.patch at call-time to isolate the
app-internal dependencies (fetch_events, get_mood_trend, etc.) — that is
far safer than clobbering real implementations in sys.modules.
"""
import sys
import types
from unittest.mock import MagicMock


def _stub(name: str) -> MagicMock:
    """Register a MagicMock in sys.modules only if not already present."""
    if name not in sys.modules:
        mock = MagicMock()
        sys.modules[name] = mock
        return mock
    return sys.modules[name]


# ---------------------------------------------------------------------------
# langchain — @tool decorator must be a transparent (identity) decorator so
# the decorated functions are plain callables in test scope.
# ---------------------------------------------------------------------------
if "langchain" not in sys.modules:
    _lc = types.ModuleType("langchain")
    sys.modules["langchain"] = _lc

if "langchain.tools" not in sys.modules:
    _lc_tools = types.ModuleType("langchain.tools")
    _lc_tools.tool = lambda f: f          # no-op decorator
    sys.modules["langchain.tools"] = _lc_tools

for _lc_mod in (
    "langchain_core",
    "langchain_core.prompts",
    "langchain_core.messages",
    "langchain_community",
):
    _stub(_lc_mod)

# ---------------------------------------------------------------------------
# pywinauto — not installed in the test environment
# ElementNotFoundError must be a real exception class so pytest.raises works.
# ---------------------------------------------------------------------------
if "pywinauto" not in sys.modules:
    _pw = MagicMock()

    class _ElementNotFoundError(Exception):
        pass

    _pw_fw = MagicMock()
    _pw_fw.ElementNotFoundError = _ElementNotFoundError
    sys.modules["pywinauto"] = _pw
    sys.modules["pywinauto.findwindows"] = _pw_fw
    _pw.Application = MagicMock()
    _pw.findwindows = _pw_fw

# ---------------------------------------------------------------------------
# Other system / GUI / network packages not installed in the test environment
# ---------------------------------------------------------------------------
for _ext_mod in ("psutil", "pyperclip", "pygetwindow", "pyautogui"):
    _stub(_ext_mod)

# requests and ddgs: stub only if absent; the real `requests` package IS
# available (used by test_web_tools for requests.exceptions.*), so we only
# stub ddgs which is not installed in the system python.
_stub("ddgs")

# ---------------------------------------------------------------------------
# pycaw — used inside mute_unmute_mic (local import inside function body).
# We stub the whole pycaw hierarchy so the `from pycaw.pycaw import ...`
# inside the tool function resolves without the real COM stack.
# Individual tests then patch pycaw.pycaw.AudioUtilities etc. at call-time.
# ---------------------------------------------------------------------------
for _pycaw_mod in ("pycaw", "pycaw.pycaw", "pycaw.api", "pycaw.utils", "comtypes"):
    _stub(_pycaw_mod)

# ---------------------------------------------------------------------------
# screen_brightness_control — imported locally inside set_brightness /
# adjust_brightness.  Individual tests patch .set_brightness / .get_brightness
# on the already-registered stub at call-time.
# ---------------------------------------------------------------------------
_stub("screen_brightness_control")

