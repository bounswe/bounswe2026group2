import logging

from app.core.logging import configure_logging


def test_configure_logging_applies_requested_log_level():
    configure_logging("WARNING")

    assert logging.getLogger().level == logging.WARNING
    assert logging.getLogger("app").level == logging.WARNING
    assert logging.getLogger("uvicorn").level == logging.WARNING
    assert logging.getLogger("uvicorn.error").level == logging.WARNING


def test_configure_logging_falls_back_to_info_for_unknown_level():
    configure_logging("NOT_A_LEVEL")

    assert logging.getLogger().level == logging.INFO
    assert logging.getLogger("app").level == logging.INFO
