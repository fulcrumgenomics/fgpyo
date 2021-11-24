"""
Abstract class for writing and parsing metric-like tab-delimited information
"""

from abc import ABC
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import TypeVar
from fgpyo.util import inspect
import attr
from typing import Callable

MetricType = TypeVar("MetricType")


@attr.s
class Metric(ABC, Generic[MetricType]):
    """Abstract base class for all metric-like tab-delimited files

    Metric files are tab-delimited, contain a header, and zero or more rows for metric values.  This
    makes it easy for them to be read in languages like `R`.
    """

    @classmethod
    def _parsers(cls) -> Dict[type, Callable[[str], Any]]:
        # TODO: doc
        return {}

    @classmethod
    def read(cls, path: Path) -> List[Any]:
        """Reads in zero or more metrics from the given path.

        The metric file must contain a matching header.

        Args:
            path: the path to the metrics file.
        """
        instances: List[Metric[MetricType]] = []
        parsers = cls._parsers()
        with path.open("r") as reader:
            header: List[str] = reader.readline().rstrip("\r\n").split("\t")
            assert header == cls.header(), "Header did not match"
            for line in reader:
                fields: List[str] = line.rstrip("\r\n").split("\t")
                instance: Metric[MetricType] = inspect.attr_from(
                    cls=cls, kwargs=dict(zip(header, fields)), parsers=parsers
                )
                instances.append(instance)
        return instances

    @classmethod
    def write(cls, path: Path, *values: MetricType) -> None:
        """Writes zero or more metrics to the given path.

        The header will always be written.

        Args:
            values: zero or more metrics.
        """
        with path.open("w") as writer:
            writer.write("\t".join(cls.header()))
            writer.write("\n")
            for value in values:
                # Important, don't recurse on nested attr classes, instead let implementing class
                # implement format_value.
                writer.write(
                    "\t".join(
                        cls.format_value(item) for item in attr.astuple(value, recurse=False)
                    )
                )
                writer.write("\n")

    @classmethod
    def header(cls) -> List[str]:
        """The list of header values for the metric."""
        return [a.name for a in attr.fields(cls)]

    @classmethod
    def format_value(cls, value: Any) -> str:
        """The default method to format values of a given type.

        By default, this method will comma-delimit `list`, `tuple`, and `set` types, and apply
        `str` to all others.

        Dictionaries / mappings will have keys and vals separated by semicolons, and key val pairs
        pairs delimited by commas.

        In addition, lists will be flanked with '[]', tuples with '()' and sets and dictionaries
        with '{}'

        Args:
            value: the value to format.
        """
        if issubclass(type(value), Enum):
            return cls.format_value(value.value)
        if isinstance(value, (tuple)):
            if len(value) == 0:
                return "()"
            else:
                return "(" + ",".join(cls.format_value(v) for v in value) + ")"
        if isinstance(value, (list)):
            if len(value) == 0:
                return "[]"
            else:
                return "[" + ",".join(cls.format_value(v) for v in value) + "]"
        if isinstance(value, (set)):
            if len(value) == 0:
                return ""
            else:
                return "{" + ",".join(cls.format_value(v) for v in value) + "}"
        elif isinstance(value, dict):
            if len(value) == 0:
                return "{}"
            else:
                return (
                    "{"
                    + ",".join(
                        f"{cls.format_value(k)};{cls.format_value(v)}" for k, v in value.items()
                    )
                    + "}"
                )
        elif isinstance(value, float):
            return str(round(value, 5))
        else:
            return str(value)

    @classmethod
    def to_list(cls, value: str) -> List[Any]:
        """Returns a list value split on comma delimeter."""
        return [] if value == "" else value.split(",")
