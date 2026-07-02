import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Allow `from app.backend...` imports when running pytest from repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# scheduler.jobs imports modifier/checkin at module load; stub them so collection
# does not pull in LLM/Chroma dependencies (out of scope for unit tests).
for _mod_name in (
    "app.backend.memory.modifier",
    "app.backend.scheduler.checkin",
):
    if _mod_name not in sys.modules:
        _stub = MagicMock()
        sys.modules[_mod_name] = _stub

_queue_stub = MagicMock()
_queue_stub.reminder_queue = MagicMock()
if "app.backend.core.queue" not in sys.modules:
    sys.modules["app.backend.core.queue"] = _queue_stub


@pytest.fixture
def events_db(tmp_path, monkeypatch):
    """Redirect sqlite_client to a temporary events database."""
    import app.backend.memory.sqlite_client as sqlite_client

    db_path = tmp_path / "events.db"
    monkeypatch.setattr(sqlite_client, "DB_PATH", db_path)
    sqlite_client.init_db()
    return sqlite_client


@pytest.fixture
def mood_db(tmp_path, monkeypatch):
    """Redirect mood_log to a temporary mood database."""
    import app.backend.mood.mood_log as mood_log

    db_path = tmp_path / "mood_log.db"
    monkeypatch.setattr(mood_log, "DB_PATH", db_path)
    mood_log.init_mood_log()
    return mood_log


@pytest.fixture
def interaction_db(tmp_path, monkeypatch):
    """Redirect interaction_log to a temporary interaction database."""
    import app.backend.mood.interaction_log as interaction_log

    db_path = tmp_path / "interaction_log.db"
    monkeypatch.setattr(interaction_log, "DB_PATH", db_path)
    interaction_log.init_interaction_log()
    return interaction_log
