"""
Metrics
-------

Module for storing, reading, and writing metric-like tab-delimited information.

Metric files are tab-delimited, contain a header, and zero or more rows for metric values.  This
makes it easy for them to be read in languages like `R`.  For example, a row per person, with
columns for age, gender, and address.

The :class:`~fgpyo.util.metric.Metric` class makes it easy to read, write, and store one or metrics
of the same type, all the while preserving types for each value in a metric.  It is an abstract
base class decorated by `attr <https://www.attrs.org/en/stable/examples.html>`_, with attributes
storing one or more typed values.

Examples
~~~~~~~~

Defining a new metric class:

.. code-block:: python

   >>> from fgpyo.util.metric import Metric
   >>> import attr
   >>> @attr.s(auto_attribs=True, frozen=True)
   ... class Person(Metric["Person"]):
   ...     name: str
   ...     age: int

Getting the attributes for a metric class.  These will be used for the header when reading and
writing metric files.

.. code-block:: python

   >>> Person.header()
   ['name', 'age']

Getting the values from a metric class instance.  The values are in the same order as the header.

.. code-block:: python

   >>> list(Person(name="Alice", age=47).values())
   ["Alice", 47]

Writing a list of metrics to a file:

.. code-block:: python

   >>> metrics = [
   ...     Person(name="Alice", age=47),
   ...     Person(name="Bob", age=24)
   ... ]
   >>> from pathlib import Path
   >>> Person.write(Path("/path/to/metrics.txt"), *metrics)

Then the contents of the written metrics file:

.. code-block:: console

   $ column -t /path/to/metrics.txt
   name   age
   Alice  47
   Bob    24

Reading the metrics file back in:

.. code-block:: python

   >>> list(Person.read(Path("/path/to/metrics.txt")))
   [Person(name='Alice', age=47, address=None), Person(name='Bob', age=24, address='North Pole')]

Formatting and parsing the values for custom types is supported by overriding the
:func:`~fgpyo.util.metric.Metric._parsers` and
:func:`~fgpyo.util.metric.Metric.format_value` methods.

.. code-block:: python

   >>> @attr.s(auto_attribs=True, frozen=True)
   ... class Name:
   ...     first: str
   ...     last: str
   ...     @classmethod
   ...     def parse(cls, value: str) -> "Name":
   ...          fields = value.split(" ")
   ...          return Name(first=fields[0], last=fields[1])
   >>> @attr.s(auto_attribs=True, frozen=True)
   ... class Person(Metric["Person"]):
   ...     name: Name
   ...     age: int
   ...     def _parsers(cls) -> Dict[type, Callable[[str], Any]]:
   ...         return {Name: lambda value: Name.parse(value=value)}
   ...     @classmethod
   ...     def format_value(cls, value: Any) -> str:
   ...         if isinstance(value, (Name)):
   ...             return f"{value.first} {value.last}"
   ...         else:
   ...             return super().format_value(value=value)
   >>> Person.parse(fields=["john doe", "42"])
   Person(name=Name(first='john', last='doe'), age=42)
   >>> Person(name=Name(first='john', last='doe'), age=42, address=None).formatted_values()
   ["first last", "42"]

"""

from abc import ABC
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import List
from typing import TypeVar

import attr

from fgpyo.util import inspect

MetricType = TypeVar("MetricType")


@attr.s
class Metric(ABC, Generic[MetricType]):
    """Abstract base class for all metric-like tab-delimited files

    Metric files are tab-delimited, contain a header, and zero or more rows for metric values.  This
    makes it easy for them to be read in languages like `R`.

    Sub-classes of :class:`~fgpyo.util.metric.Metric` can support parsing and formatting custom
    types with :func::`~fgpyo.util.metric.Metric._parsers` and
    :func::`~fgpyo.util.metric.Metric.format_value`.
    """

    def values(self) -> Iterator[Any]:
        """An iterator over attribute values in the same order as the header."""
        return iter(attr.astuple(self, recurse=False))

    def formatted_values(self) -> Iterator[str]:
        """An iterator over formatted attribute values in the same order as the header."""
        return [self.format_value(value) for value in self.values()]

    @classmethod
    def _parsers(cls) -> Dict[type, Callable[[str], Any]]:
        """Mapping of type to a specific parser for that type.  The parser must accept a string
        as a single parameter and return a single value of the given type.  Sub-classes may
        override this method to support custom types."""
        return {}

    @classmethod
    def read(cls, path: Path) -> Iterator[Any]:
        """Reads in zero or more metrics from the given path.

        The metric file must contain a matching header.

        Args:
            path: the path to the metrics file.
        """
        parsers = cls._parsers()
        with path.open("r") as reader:
            header: List[str] = reader.readline().rstrip("\r\n").split("\t")
            assert header == cls.header(), "Header did not match"
            for line in reader:
                fields: List[str] = line.rstrip("\r\n").split("\t")
                instance: Metric[MetricType] = inspect.attr_from(
                    cls=cls, kwargs=dict(zip(header, fields)), parsers=parsers
                )
                yield instance

    @classmethod
    def parse(cls, fields: List[str]) -> Any:
        """Parses the string-representation of this metric.  One string per attribute should be
        given."""
        parsers = cls._parsers()
        header = cls.header()
        assert len(fields) == len(header)
        return inspect.attr_from(cls=cls, kwargs=dict(zip(header, fields)), parsers=parsers)

    @classmethod
    def write(cls, path: Path, *values: MetricType) -> None:
        """Writes zero or more metrics to the given path.

        The header will always be written.

        Args:
            path: path to the output file
            values: zero or more metrics.
        """
        with path.open("w") as writer:
            writer.write("\t".join(cls.header()))
            writer.write("\n")
            for value in values:
                # Important, don't recurse on nested attr classes, instead let implementing class
                # implement format_value.
                writer.write("\t".join(cls.format_value(item) for item in value.values()))
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
                return ""
            else:
                return ",".join(cls.format_value(v) for v in value)
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
        elif value is None:
            return ""
        else:
            return str(value)

    @classmethod
    def to_list(cls, value: str) -> List[Any]:
        """Returns a list value split on comma delimeter."""
        return [] if value == "" else value.split(",")
