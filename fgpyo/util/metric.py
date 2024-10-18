"""
# Metrics

Module for storing, reading, and writing metric-like tab-delimited information.

Metric files are tab-delimited, contain a header, and zero or more rows for metric values.  This
makes it easy for them to be read in languages like `R`.  For example, a row per person, with
columns for age, gender, and address.

The [`Metric()`][fgpyo.util.metric.Metric] class makes it easy to read, write, and store
one or metrics of the same type, all the while preserving types for each value in a metric.  It is
an abstract base class decorated by
[`@dataclass`](https://docs.python.org/3/library/dataclasses.html), or
[`@attr.s`](https://www.attrs.org/en/stable/examples.html), with attributes storing one or more
typed values. If using multiple layers of inheritance, keep in mind that it's not possible to mix
these dataclass utils, e.g. a dataclasses class derived from an attr class will not appropriately
initialize the values of the attr superclass.

## Examples

Defining a new metric class:

```python
   >>> from fgpyo.util.metric import Metric
   >>> import dataclasses
   >>> @dataclasses.dataclass(frozen=True)
   ... class Person(Metric["Person"]):
   ...     name: str
   ...     age: int
```

or using attr:

```python
   >>> from fgpyo.util.metric import Metric
   >>> import attr
   >>> @attr.s(auto_attribs=True, frozen=True)
   ... class Person(Metric["Person"]):
   ...     name: str
   ...     age: int
```

Getting the attributes for a metric class.  These will be used for the header when reading and
writing metric files.

```python
   >>> Person.header()
   ['name', 'age']
```

Getting the values from a metric class instance.  The values are in the same order as the header.

```python
   >>> list(Person(name="Alice", age=47).values())
   ["Alice", 47]
```

Writing a list of metrics to a file:

```python
   >>> metrics = [
   ...     Person(name="Alice", age=47),
   ...     Person(name="Bob", age=24)
   ... ]
   >>> from pathlib import Path
   >>> Person.write(Path("/path/to/metrics.txt"), *metrics)
```

Then the contents of the written metrics file:

```python
   $ column -t /path/to/metrics.txt
   name   age
   Alice  47
   Bob    24
```

Reading the metrics file back in:

```python
   >>> list(Person.read(Path("/path/to/metrics.txt")))
   [Person(name='Alice', age=47, address=None), Person(name='Bob', age=24, address='North Pole')]
```

Formatting and parsing the values for custom types is supported by overriding the `_parsers()` and
[`format_value()`][fgpyo.util.metric.Metric.format_value] methods.

```python
   >>> @dataclasses.dataclass(frozen=True)
   ... class Name:
   ...     first: str
   ...     last: str
   ...     @classmethod
   ...     def parse(cls, value: str) -> "Name":
   ...          fields = value.split(" ")
   ...          return Name(first=fields[0], last=fields[1])
   >>> @dataclasses.dataclass(frozen=True)
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
```
"""

import dataclasses
import sys
from abc import ABC
from contextlib import AbstractContextManager
from csv import DictWriter
from dataclasses import dataclass
from enum import Enum
from inspect import isclass
from io import TextIOWrapper
from pathlib import Path
from types import TracebackType
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generic
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

from fgpyo import io
from fgpyo.util import inspect

MetricType = TypeVar("MetricType", bound="Metric")


@dataclass(frozen=True)
class MetricFileHeader:
    """
    Header of a file.

    A file's header contains an optional preamble, consisting of lines prefixed by a comment
    character and/or empty lines, and a required row of fieldnames before the data rows begin.

    Attributes:
        preamble: A list of any lines preceding the fieldnames.
        fieldnames: The field names specified in the final line of the header.
    """

    preamble: List[str]
    fieldnames: List[str]


class Metric(ABC, Generic[MetricType]):
    """Abstract base class for all metric-like tab-delimited files

    Metric files are tab-delimited, contain a header, and zero or more rows for metric values.  This
    makes it easy for them to be read in languages like `R`.

    Subclasses of [`Metric()`][fgpyo.util.metric.Metric] can support parsing and
    formatting custom types with `_parsers()` and
    [`format_value()`][fgpyo.util.metric.Metric.format_value].
    """

    @classmethod
    def keys(cls) -> Iterator[str]:
        """An iterator over field names in the same order as the header."""
        for field in inspect.get_fields(cls):  # type: ignore[arg-type]
            yield field.name

    def values(self) -> Iterator[Any]:
        """An iterator over attribute values in the same order as the header."""
        for field in inspect.get_fields(self.__class__):  # type: ignore[arg-type]
            yield getattr(self, field.name)

    def items(self) -> Iterator[Tuple[str, Any]]:
        """
        An iterator over field names and their corresponding values in the same order as the header.
        """
        for field in inspect.get_fields(self.__class__):  # type: ignore[arg-type]
            yield (field.name, getattr(self, field.name))

    def formatted_values(self) -> List[str]:
        """An iterator over formatted attribute values in the same order as the header."""
        return [self.format_value(value) for value in self.values()]

    def formatted_items(self) -> List[Tuple[str, str]]:
        """An iterator over formatted attribute values in the same order as the header."""
        return [(key, self.format_value(value)) for key, value in self.items()]

    @classmethod
    def _parsers(cls) -> Dict[type, Callable[[str], Any]]:
        """Mapping of type to a specific parser for that type.  The parser must accept a string
        as a single parameter and return a single value of the given type.  Sub-classes may
        override this method to support custom types."""
        return {}

    @classmethod
    def read(cls, path: Path, ignore_extra_fields: bool = True) -> Iterator[Any]:
        """Reads in zero or more metrics from the given path.

        The metric file must contain a matching header.

        Columns that are not present in the file but are optional in the metric class will
        be default values.

        Args:
            path: the path to the metrics file.
            ignore_extra_fields: True to ignore any extra columns, False to raise an exception.
        """
        parsers = cls._parsers()
        with io.to_reader(path) as reader:
            header: List[str] = reader.readline().rstrip("\r\n").split("\t")
            # check the header
            class_fields = set(cls.header())
            file_fields = set(header)
            missing_from_class = file_fields.difference(class_fields)
            missing_from_file = class_fields.difference(file_fields)

            field_name_to_attribute = inspect.get_fields_dict(cls)  # type: ignore[arg-type]

            # ignore class fields that are missing from the file (via header) if they're optional
            # or have a default
            if len(missing_from_file) > 0:
                fields_with_defaults = [
                    field
                    for field in missing_from_file
                    if inspect._attribute_has_default(field_name_to_attribute[field])
                ]
                # remove optional class fields from the fields
                missing_from_file = missing_from_file.difference(fields_with_defaults)

            # raise an exception if there are non-optional class fields missing from the file
            if len(missing_from_file) > 0:
                raise ValueError(
                    f"In file: {path}, fields in file missing from class '{cls.__name__}': "
                    + ", ".join(missing_from_file)
                )

            # raise an exception if there are fields in the file not in the header, unless they
            # should be ignored.
            if not ignore_extra_fields and len(missing_from_class) > 0:
                raise ValueError(
                    f"In file: {path}, extra fields in file missing from class '{cls.__name__}': "
                    ", ".join(missing_from_file)
                )

            # read the metric lines
            for lineno, line in enumerate(reader, 2):
                # parse the raw values
                values: List[str] = line.rstrip("\r\n").split("\t")

                # raise an exception if there aren't the same number of values as the header
                if len(header) != len(values):
                    raise ValueError(
                        f"In file: {path}, expected {len(header)} columns, got {len(values)} on "
                        f"line {lineno}: {line}"
                    )

                # build the metric
                instance: Metric[MetricType] = inspect.attr_from(
                    cls=cls, kwargs=dict(zip(header, values)), parsers=parsers
                )
                yield instance

    @classmethod
    def parse(cls, fields: List[str]) -> Any:
        """Parses the string-representation of this metric.  One string per attribute should be
        given.

        """
        parsers = cls._parsers()
        header = cls.header()
        assert len(fields) == len(header)
        return inspect.attr_from(cls=cls, kwargs=dict(zip(header, fields)), parsers=parsers)

    @classmethod
    def write(cls, path: Path, *values: MetricType) -> None:
        """Writes zero or more metrics to the given path.

        The header will always be written.

        Args:
            path: Path to the output file.
            values: Zero or more metrics.

        """
        with MetricWriter[MetricType](path, metric_class=cls) as writer:
            writer.writeall(values)

    @classmethod
    def header(cls) -> List[str]:
        """The list of header values for the metric."""
        return [a.name for a in inspect.get_fields(cls)]  # type: ignore[arg-type]

    @classmethod
    def format_value(cls, value: Any) -> str:  # noqa: C901
        """The default method to format values of a given type.

        By default, this method will comma-delimit `list`, `tuple`, and `set` types, and apply
        `str` to all others.

        Dictionaries / mappings will have keys and vals separated by semicolons, and key val pairs
        delimited by commas.

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

    @staticmethod
    def fast_concat(*inputs: Path, output: Path) -> None:
        if len(inputs) == 0:
            raise ValueError("No inputs provided")

        headers = [next(io.read_lines(input_path)) for input_path in inputs]
        assert len(set(headers)) == 1, "Input headers do not match"
        io.write_lines(path=output, lines_to_write=set(headers))

        for input_path in inputs:
            io.write_lines(
                path=output, lines_to_write=list(io.read_lines(input_path))[1:], append=True
            )

    @staticmethod
    def _read_header(
        reader: TextIOWrapper,
        delimiter: str = "\t",
        comment_prefix: str = "#",
    ) -> MetricFileHeader:
        """
        Read the header from an open file.

        The first row after any commented or empty lines will be used as the fieldnames.

        Lines preceding the fieldnames will be returned in the `preamble`. Leading and trailing
        whitespace are removed and ignored.

        Args:
            reader: An open, readable file handle.
            file_format: A dataclass containing (at minimum) the file's delimiter and the string
                prefixing any comment lines.

        Returns:
            A `MetricFileHeader` containing the field names and any preceding lines.

        Raises:
            ValueError: If the file was empty or contained only comments or empty lines.
        """

        preamble: List[str] = []

        for line in reader:
            if line.strip().startswith(comment_prefix) or line.strip() == "":
                # Skip any commented or empty lines before the header
                preamble.append(line.strip())
            else:
                # The first line with any other content is assumed to be the header
                fieldnames = line.strip().split(delimiter)
                break
        else:
            # If the file was empty, kick back an empty header
            fieldnames = []

        return MetricFileHeader(preamble=preamble, fieldnames=fieldnames)


def _is_metric_class(cls: Any) -> TypeGuard[Metric]:
    """True if the given class is a Metric."""

    is_metric_cls: bool = isclass(cls) and issubclass(cls, Metric)

    try:
        import attr

        is_metric_cls = is_metric_cls and (dataclasses.is_dataclass(cls) or attr.has(cls))
    except ImportError:
        is_metric_cls = is_metric_cls and dataclasses.is_dataclass(cls)

    return is_metric_cls


class MetricWriter(Generic[MetricType], AbstractContextManager):
    _metric_class: Type[Metric]
    _fieldnames: List[str]
    _fout: TextIOWrapper
    _writer: DictWriter

    def __init__(
        self,
        filename: Union[Path, str],
        metric_class: Type[Metric],
        append: bool = False,
        delimiter: str = "\t",
        include_fields: Optional[List[str]] = None,
        exclude_fields: Optional[List[str]] = None,
    ) -> None:
        """
        Args:
            filename: Path to the file to write.
            metric_class: Metric class.
            append: If `True`, the file will be appended to. Otherwise, the specified file will be
                overwritten.
            delimiter: The output file delimiter.
            include_fields: If specified, only the listed fieldnames will be included when writing
                records to file. Fields will be written in the order provided.
                May not be used together with `exclude_fields`.
            exclude_fields: If specified, any listed fieldnames will be excluded when writing
                records to file.
                May not be used together with `include_fields`.

        Raises:
            TypeError: If the provided metric class is not a dataclass- or attr-decorated
                subclass of `Metric`.
            AssertionError: If the provided filepath is not writable.
            AssertionError: If `append=True` and the provided file is not readable. (When appending,
                we check to ensure that the header matches the specified metric class. The file must
                be readable to get the header.)
            ValueError: If `append=True` and the provided file is a FIFO (named pipe).
            ValueError: If `append=True` and the provided file does not include a header.
            ValueError: If `append=True` and the header of the provided file does not match the
                specified metric class and the specified include/exclude fields.
        """

        filepath: Path = Path(filename)
        if (filepath.is_fifo() or filepath.is_char_device()) and append:
            raise ValueError("Cannot append to stdout, stderr, or other named pipe or stream")

        ordered_fieldnames: List[str] = _validate_and_generate_final_output_fieldnames(
            metric_class=metric_class,
            include_fields=include_fields,
            exclude_fields=exclude_fields,
        )

        _assert_is_metric_class(metric_class)
        io.assert_path_is_writable(filepath)
        if append:
            io.assert_path_is_readable(filepath)
            _assert_file_header_matches_metric(
                path=filepath,
                metric_class=metric_class,
                ordered_fieldnames=ordered_fieldnames,
                delimiter=delimiter,
            )

        self._metric_class = metric_class
        self._fieldnames = ordered_fieldnames
        self._fout = io.to_writer(filepath, append=append)
        self._writer = DictWriter(
            f=self._fout,
            fieldnames=self._fieldnames,
            delimiter=delimiter,
        )

        # If we aren't appending to an existing file, write the header before any rows
        if not append:
            self._writer.writeheader()

    def __enter__(self) -> "MetricWriter":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        self.close()
        super().__exit__(exc_type, exc_value, traceback)

    def close(self) -> None:
        """Close the underlying file handle."""
        self._fout.close()

    def write(self, metric: MetricType) -> None:
        """
        Write a single Metric instance to file.

        The Metric is converted to a dictionary and then written using the underlying
        `csv.DictWriter`. If the `MetricWriter` was created using the `include_fields` or
        `exclude_fields` arguments, the fields of the Metric are subset and/or reordered
        accordingly before writing.

        Args:
            metric: An instance of the specified Metric.

        Raises:
            TypeError: If the provided `metric` is not an instance of the Metric class used to
                parametrize the writer.
        """

        # Serialize the Metric to a dict for writing by the underlying `DictWriter`
        row = {fieldname: val for fieldname, val in metric.formatted_items()}

        # Filter and/or re-order output fields if necessary
        row = {fieldname: row[fieldname] for fieldname in self._fieldnames}

        self._writer.writerow(row)

    def writeall(self, metrics: Iterable[MetricType]) -> None:
        """
        Write multiple Metric instances to file.

        Each Metric is converted to a dictionary and then written using the underlying
        `csv.DictWriter`. If the `MetricWriter` was created using the `include_fields` or
        `exclude_fields` arguments, the attributes of each Metric are subset and/or reordered
        accordingly before writing.

        Args:
            metrics: A sequence of instances of the specified Metric.
        """
        for metric in metrics:
            self.write(metric)


def _validate_and_generate_final_output_fieldnames(
    metric_class: Type[MetricType],
    include_fields: Optional[List[str]] = None,
    exclude_fields: Optional[List[str]] = None,
) -> List[str]:
    """
    Subset and/or re-order the Metric's fieldnames based on the specified include/exclude lists.

    * Only one of `include_fields` and `exclude_fields` may be specified.
    * All fieldnames specified in `include_fields` must be fields on `metric_class`. If this
      argument is specified, fields will be returned in the order they appear in the list.
    * All fieldnames specified in `exclude_fields` must be fields on `metric_class`. (This is
      technically unnecessary, but is a safeguard against passing an incorrect list.)
    * If neither `include_fields` or `exclude_fields` are specified, return the `metric_class`'s
      fieldnames, in the order they are defined on the `metric_class`.

    Raises:
        ValueError: If both `include_fields` and `exclude_fields` are specified.
    """

    if include_fields is not None and exclude_fields is not None:
        raise ValueError(
            "Only one of `include_fields` and `exclude_fields` may be specified, not both."
        )
    elif exclude_fields is not None:
        _assert_fieldnames_are_metric_attributes(exclude_fields, metric_class)
        output_fieldnames = [f for f in metric_class.keys() if f not in exclude_fields]
    elif include_fields is not None:
        _assert_fieldnames_are_metric_attributes(include_fields, metric_class)
        output_fieldnames = include_fields
    else:
        output_fieldnames = list(metric_class.keys())

    return output_fieldnames


def _assert_file_header_matches_metric(
    path: Path,
    metric_class: Type[MetricType],
    delimiter: str,
    ordered_fieldnames: Optional[List[str]] = None,
) -> None:
    """
    Check that the specified file has a header and its fields match those of the provided Metric.

    Args:
        path: A path to a `Metric` file.
        metric_class: The `Metric` class to validate against.
        delimiter: The delimiter to use when reading the header.
        ordered_fieldnames: An optional ordering of the fieldnames in the header.

    Raises:
        ValueError: If the provided file does not include a header.
        ValueError: If the header of the provided file does not match the provided Metric (or list
            of ordered fieldnames, if provided).
    """
    _assert_is_metric_class(metric_class)

    with path.open("r") as fin:
        header: MetricFileHeader = metric_class._read_header(fin, delimiter=delimiter)

    if header.fieldnames == []:
        raise ValueError(f"Could not find a header in the provided file: {path}")

    fieldnames: List[str] = (
        ordered_fieldnames if ordered_fieldnames is not None else list(metric_class.keys())
    )

    if header.fieldnames != fieldnames:
        raise ValueError(
            "The provided file does not have the same field names as the provided Metric:\n"
            f"\tMetric: {metric_class.__name__}\n"
            f"\tFile: {path}\n"
            f"\tExpected fields: {', '.join(fieldnames)}\n"
            f"\tActual fields: {', '.join(header.fieldnames)}\n"
        )


def _assert_fieldnames_are_metric_attributes(
    specified_fieldnames: List[str],
    metric_class: Type[MetricType],
) -> None:
    """
    Check that all of the specified fields are attributes on the given Metric.

    Raises:
        ValueError: if any of the specified fieldnames are not an attribute on the given Metric.
    """
    _assert_is_metric_class(metric_class)

    invalid_fieldnames = {f for f in specified_fieldnames if f not in list(metric_class.keys())}

    if len(invalid_fieldnames) > 0:
        raise ValueError(
            "One or more of the specified fields are not attributes on the Metric "
            + f"{metric_class.__name__}: "
            + ", ".join(invalid_fieldnames)
        )


def _assert_is_metric_class(cls: Type[Metric]) -> None:
    """
    Assert that the given class is a Metric.

    Args:
        cls: A class object.

    Raises:
        TypeError: If the given class is not a Metric.
    """
    if not _is_metric_class(cls):
        raise TypeError(f"Not a dataclass or attr decorated Metric: {cls}")
