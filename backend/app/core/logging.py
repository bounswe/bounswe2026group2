import logging
import sys


def configure_logging(log_level: str) -> None:
    """Configure app logs for Render stdout/stderr collection."""
    normalized_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=normalized_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )

    # Keep framework loggers aligned so Render and log streams can filter by level.
    for logger_name in ("app", "uvicorn", "uvicorn.error"):
        logging.getLogger(logger_name).setLevel(normalized_level)
