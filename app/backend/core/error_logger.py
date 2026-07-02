import logging
import traceback
from pathlib import Path

_LOG_PATH = Path(__file__).parent.parent / "data" / "error.log"
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(_LOG_PATH),
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_logger = logging.getLogger("cyclone.errors")


def log_error(context: str, exception: Exception) -> None:
    """Log a structured error entry to data/error.log.

    Args:
        context: Short description of where/what failed (e.g. "tool:get_weather").
        exception: The caught exception instance.
    """
    tb = traceback.format_exc()
    _logger.error(
        "[%s] %s: %s\n%s",
        context,
        type(exception).__name__,
        exception,
        tb,
    )
