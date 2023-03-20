"""
Methods for setting up logging for tools.
-----------------------------------------

Progress Logging Examples
~~~~~~~~~~~~~~~~~~~~~~~~~

Frequently input data (SAM/BAM/CRAM/VCF) are iterated in genomic coordinate order.  Logging
progress is useful to not only log how many inputs have been consumed, but also their genomic
coordinate.  :class:`~fgpyo.util.logging.ProgressLogger` can log progress every fixed number of
records.  Logging can be written to :class:`logging.Logger` as well as custom print method.

.. code-block:: python

   >>> from fgpyo.util.logging import ProgressLogger
   >>> logged_lines = []
   >>> progress = ProgressLogger(
   ...     printer=lambda s: logged_lines.append(s),
   ...     verb="recorded",
   ...     noun="items",
   ...     unit=2
   ... )
   >>> progress.record(reference_name="chr1", position=1)  # does not log
   False
   >>> progress.record(reference_name="chr1", position=2)  # logs
   True
   >>> progress.record(reference_name="chr1", position=3)  # does not log
   False
   >>> progress.log_last()  # will log the last recorded item, if not previously logged
   True
   >>> logged_lines  # show the lines logged
   ['recorded 2 items: chr1:2', 'recorded 3 items: chr1:3']

"""

import logging

try:  # py>=38
    from typing import Literal
except ImportError:  # py<38
    from typing_extensions import Literal
import socket
from contextlib import AbstractContextManager
from logging import Logger
from threading import RLock
from typing import Any
from typing import Callable
from typing import Optional
from typing import Union

from pysam import AlignedSegment

# Global that is set to True once logging initialization is run to prevent running > once.
__FGPYO_LOGGING_SETUP: bool = False

# A lock used to make sure initialization is performed only once
__LOCK = RLock()


def setup_logging(level: str = "INFO", name: str = "fgpyo") -> None:
    """Globally configure logging for all modules

    Configures logging to run at a specific level and output messages to stderr with
    useful information preceding the actual log message.

    Args:
        level: the default level for the logger
        name: the name of the logger
    """
    global __FGPYO_LOGGING_SETUP

    with __LOCK:
        if not __FGPYO_LOGGING_SETUP:
            format = (
                f"%(asctime)s {socket.gethostname()} %(name)s:%(funcName)s:%(lineno)s "
                + "[%(levelname)s]: %(message)s"
            )
            handler = logging.StreamHandler()
            handler.setLevel(level)
            handler.setFormatter(logging.Formatter(format))

            logger = logging.getLogger(name)
            logger.setLevel(level)
            logger.addHandler(handler)
        else:
            logging.getLogger(__name__).warn("Logging already initialized.")

        __FGPYO_LOGGING_SETUP = True


class ProgressLogger(AbstractContextManager):
    """A little class to track progress.

    This will output a log message every `unit` number times recorded.

    Attributes:
        printer: either a Logger (in which case progress will be printed at Info) or a lambda
            that consumes a single string
        noun: the noun to use in the log message
        verb: the verb to use in the log message
        unit: the number of items for every log message
        count: the total count of items recorded
    """

    def __init__(
        self,
        printer: Union[Logger, Callable[[str], Any]],
        noun: str = "records",
        verb: str = "Read",
        unit: int = 100000,
    ) -> None:
        if isinstance(printer, Logger):
            self.printer = lambda s: printer.info(s)
        else:
            self.printer = printer
        self.noun: str = noun
        self.verb: str = verb
        self.unit: int = unit
        self.count: int = 0
        self._count_mod_unit: int = 0
        self._last_reference_name: Optional[str] = None
        self._last_position: Optional[int] = None

    def __exit__(
        self, ex_type: Optional[Any], ex_value: Optional[Any], traceback: Optional[Any]
    ) -> Literal[False]:
        if ex_value is None:
            self.log_last()
        return False

    def record(
        self,
        reference_name: Optional[str] = None,
        position: Optional[int] = None,
    ) -> bool:
        """Record an item at a given genomic coordinate.
        Args:
            reference_name: the reference name of the item
            position: the 1-based start position of the item
        Returns:
            true if a message was logged, false otherwise
        """
        self.count += 1
        self._count_mod_unit += 1
        self._last_reference_name = reference_name
        self._last_position = None if position is None or position <= 0 else position
        if self._count_mod_unit == self.unit:
            self._count_mod_unit = 0
            self._log(refname=self._last_reference_name, position=self._last_position)
            return True
        else:
            return False

    def record_alignment(
        self,
        rec: AlignedSegment,
    ) -> bool:
        """Correctly record pysam.AlignedSegments (zero-based coordinates).

        Args:
            rec: pysam.AlignedSegment object

        Returns:
            true if a message was logged, false otherwise
        """
        if rec.reference_start is None:
            return self.record(None, None)
        else:
            return self.record(rec.reference_name, rec.reference_start + 1)

    def _log(
        self,
        refname: Optional[str] = None,
        position: Optional[int] = None,
    ) -> None:
        """Helper method to print the log message.

        Args:
            refname: the name of the reference of the item
            position: the 1-based start position of the item

        Returns:
            None
        """
        coordinate: str
        if refname is None and position is None:
            coordinate = "NA"
        else:
            assert refname is not None and position is not None, f"{refname} {position}"
            coordinate = f"{refname}:{position:,d}"

        self.printer(f"{self.verb} {self.count:,d} {self.noun}: {coordinate}")

    def log_last(
        self,
    ) -> bool:
        """Force logging the last record, for example when progress has completed."""
        if self._count_mod_unit != 0:
            self._log(refname=self._last_reference_name, position=self._last_position)
            return True
        else:
            return False
