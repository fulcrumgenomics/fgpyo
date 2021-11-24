import logging

from fgpyo.util.logging import ProgressLogger


def test_progress_logger() -> None:
    logger = logging.getLogger(__name__)
    progress: ProgressLogger = ProgressLogger(printer=logger, noun="noun", verb="verb", unit=3)
    assert not progress.record()
    assert not progress.record()
    assert progress.record()
    assert not progress.log_last()  # since it was logged
    assert not progress.record()
    assert progress.log_last()  # since it hasn't been logged


def test_progress_logger_with_custom_printer() -> None:
    ss = []
    progress = ProgressLogger(printer=lambda s: ss.append(s), noun="things", verb="saw", unit=2)
    for i in range(0, 4):
        progress.record()

    assert ss == ["saw 2 things: NA", "saw 4 things: NA"]


def test_progress_logger_as_context_manager() -> None:
    ss = []
    with ProgressLogger(printer=lambda s: ss.append(s), noun="xs", verb="saw", unit=9) as progress:
        for i in range(0, 7):
            progress.record()

    assert ss == ["saw 7 xs: NA"]
