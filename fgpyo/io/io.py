"""
I/O
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

import gzip
import os
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional

import attr


# TODO ask Tim/Nils if I should only use pathlib or os
@attr.s(frozen=True, auto_attribs=True)
class IO:
    """
    Doc string place holder
    """

    paths: List[Path]
    extension: Optional[str] = None

    def _file_exists(self, path: Path) -> bool:
        """ Checks that file exists """
        if path.is_file():
            return True
        else:
            raise FileNotFoundError

    def _directory_exists(self, path: Path) -> bool:
        """ Checks that directory exists """
        if path.is_dir():
            return True
        else:
            raise NotADirectoryError

    def _readable(self, path: Path) -> bool:
        """ Checks path is readable """
        if os.access(path, os.R_OK):
            return True
        else:
            raise Exception(f"{path} is not readable")

    def _writeable(self, path: Path) -> bool:
        """ Checks that path is writable """
        if os.access(path, os.W_OK):
            return True
        else:
            raise Exception(f"{path} is not writeable")

    def paths_are_writeable(self) -> None:
        """Checks that each path is paths exist and are directories"""
        for path in self.paths:
            # Is path a directory or a path?
            if self._file_exists(path=path):
                path_is_file: bool = True
            elif self._directory_exists(path=path):
                path_is_file = False
            else:
                raise OSError(f"{path} is neither file or directory")

            if path_is_file:
                parent_dir = path.parent.absolute()
                if self._directory_exists(path=parent_dir):
                    # Check that directory is writeable
                    if self._writeable(parent_dir) and self._writeable(path=Path(path.name)):
                        print("It works!")
                    else:
                        raise Exception(f"{parent_dir} and or {path.name} are not writeable")

    def reader(self) -> Any:
        """Opens a Path for reading and based on extension uses open() or gzip.open()"""
        special_suffix: set[str] = {".gz", ".bgz"}
        for path in self.paths:
            if path.suffix in special_suffix:
                return gzip.open(path, "r")
            else:
                return path.open("r")

    def writer(self) -> Any:
        """Opens a Path for reading and based on extension uses open() or gzip.open()"""
        special_suffix: set[str] = {".gz", ".bgz"}
        for path in self.paths:
            if path.suffix in special_suffix:
                return gzip.open(path, "w")
            else:
                return path.open("w")


# def reader(self) -> None:


# example = IO([Path("dummy.txt")])
# example.paths_are_writeable()
