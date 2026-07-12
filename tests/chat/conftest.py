"""tests/chat/conftest.py

Pre-stub truly-external / non-installable modules before any chat module is
imported during pytest collection.  Mirrors the langchain/langchain_core
stubbing from tests/tools/conftest.py and additionally stubs the two heavy
app-internal modules that chain.py imports at module level (llm and agent),
so that `import app.backend.chat.chain as chain` in test_confirmation_intercept.py
succeeds without pulling in real LLM / langchain_openai dependencies.

Key design decision: we do NOT stub app.backend.core itself — it is a real
package on disk with an empty __init__.py, so we import it for real.  This
ensures `app.backend.core` is in sys.modules as a proper package BEFORE
chain.py runs `import app.backend.core.llm as llm_module`.  Python's import
machinery traverses the full parent chain even when the leaf (llm) is already
in sys.modules; if any parent package is missing the traversal fails.
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
# Must be done BEFORE any app.backend module is imported.
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
# langchain_openai — chain.py → app.backend.core.llm imports this.
# Stubbing prevents real langchain_core submodule resolution (which would
# crash because langchain_core is a MagicMock above, not a real package).
# ---------------------------------------------------------------------------
for _mod in (
    "langchain_openai",
    "langchain_openai.chat_models",
):
    _stub(_mod)

# ---------------------------------------------------------------------------
# app.backend.core — import as a REAL package so sys.modules["app.backend.core"]
# is a proper package entry.  chain.py does:
#   import app.backend.core.llm as llm_module
# Python's import machinery traverses the full parent chain (app → app.backend
# → app.backend.core) even when the leaf app.backend.core.llm is already
# stubbed in sys.modules.  If app.backend.core is absent, the traversal fails
# with "cannot import name 'core' from 'app.backend' (unknown location)".
# app/backend/core/__init__.py is empty so this import has no side effects.
# ---------------------------------------------------------------------------
import app.backend.core  # noqa: F401  (side-effect: registers the real package)

# ---------------------------------------------------------------------------
# app.backend.core.llm — chain.py lines 3-4.  Stub after core is real.
# ---------------------------------------------------------------------------
_stub("app.backend.core.llm")

# ---------------------------------------------------------------------------
# app.backend.chat.agent — chain.py line 31.
# ---------------------------------------------------------------------------
_stub("app.backend.chat.agent")

# ---------------------------------------------------------------------------
# openai — chain.py imports RateLimitError from openai.
# ---------------------------------------------------------------------------
_stub("openai")
