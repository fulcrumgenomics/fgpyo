import enum
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import attr
import pytest
from py._path.local import LocalPath as TmpDir

from fgpyo.util.metric import Metric


class EnumTest(enum.Enum):
    EnumVal1 = "val1"
    EnumVal2 = "val2"
    EnumVal3 = "val3"


@attr.s(auto_attribs=True, frozen=True)
class DummyMetric(Metric["DummyMetric"]):
    int_value: int
    str_value: str
    bool_val: bool
    enum_val: EnumTest = attr.ib()
    optional_str_value: Optional[str] = attr.ib()
    optional_int_value: Optional[int] = attr.ib()
    optional_bool_value: Optional[bool] = attr.ib()
    optional_enum_value: Optional[EnumTest] = attr.ib()
    dict_value: Dict[int, str] = attr.ib()
    tuple_value: Tuple[int, str] = attr.ib()
    list_value: List[str] = attr.ib()
    complex_value: Dict[
        int,
        Dict[
            Tuple[int, int],
            Set[str],
        ],
    ] = attr.ib()


DUMMY_METRICS: List[DummyMetric] = [
    DummyMetric(
        int_value=1,
        str_value="2",
        bool_val=True,
        enum_val=EnumTest.EnumVal1,
        optional_str_value="test4",
        optional_int_value=-5,
        optional_bool_value=True,
        optional_enum_value=EnumTest.EnumVal3,
        dict_value={
            1: "test1",
        },
        tuple_value=(0, "test1"),
        list_value=[],
        complex_value={1: {(5, 1): set({"mapped_test_val1", "setval2"})}},
    ),
    DummyMetric(
        int_value=1,
        str_value="2",
        bool_val=False,
        enum_val=EnumTest.EnumVal2,
        optional_str_value="test",
        optional_int_value=1,
        optional_bool_value=False,
        optional_enum_value=EnumTest.EnumVal1,
        dict_value={2: "test2", 7: "test4"},
        tuple_value=(1, "test2"),
        list_value=["1"],
        complex_value={2: {(-5, 1): set({"mapped_test_val2", "setval2"})}},
    ),
    DummyMetric(
        int_value=1,
        str_value="2",
        bool_val=False,
        enum_val=EnumTest.EnumVal3,
        optional_str_value=None,
        optional_int_value=None,
        optional_bool_value=None,
        optional_enum_value=None,
        dict_value={},
        tuple_value=(2, "test3"),
        list_value=["1", "2", "3"],
        complex_value={3: {(8, 1): set({"mapped_test_val3", "setval2"})}},
    ),
]


@attr.s(auto_attribs=True, frozen=True)
class Person(Metric["Person"]):
    name: Optional[str]
    age: Optional[int]


@attr.s(auto_attribs=True, frozen=True)
class Name:
    first: str
    last: str

    @classmethod
    def parse(cls, value: str) -> "Name":
        fields = value.split(" ")
        return Name(first=fields[0], last=fields[1])


@attr.s(auto_attribs=True, frozen=True)
class NamedPerson(Metric["NamedPerson"]):
    name: Name
    age: int

    @classmethod
    def _parsers(cls) -> Dict[type, Callable[[str], Any]]:
        return {Name: lambda value: Name.parse(value=value)}

    @classmethod
    def format_value(cls, value: Any) -> str:
        if isinstance(value, (Name)):
            return f"{value.first} {value.last}"
        else:
            return super().format_value(value=value)


@pytest.mark.parametrize("metric", DUMMY_METRICS)
def test_metric_roundtrip(tmpdir: TmpDir, metric: DummyMetric) -> None:
    path: Path = Path(tmpdir) / "metrics.txt"

    DummyMetric.write(path, metric)
    metrics: List[DummyMetric] = list(DummyMetric.read(path=path))

    assert len(metrics) == 1
    assert metrics[0] == metric


def test_metrics_roundtrip(tmpdir: TmpDir) -> None:
    path: Path = Path(tmpdir) / "metrics.txt"

    DummyMetric.write(path, *DUMMY_METRICS)
    metrics: List[DummyMetric] = list(DummyMetric.read(path=path))

    assert len(metrics) == len(DUMMY_METRICS)
    assert metrics == DUMMY_METRICS


def test_metric_header() -> None:
    assert DummyMetric.header() == [
        "int_value",
        "str_value",
        "bool_val",
        "enum_val",
        "optional_str_value",
        "optional_int_value",
        "optional_bool_value",
        "optional_enum_value",
        "dict_value",
        "tuple_value",
        "list_value",
        "complex_value",
    ]


def test_metric_values() -> None:
    assert list(Person(name="name", age=42).values()) == ["name", 42]


def test_metric_parse() -> None:
    assert Person.parse(fields=["name", "42"]) == Person(name="name", age=42)


def test_metric_formatted_values() -> None:
    assert Person(name="name", age=42).formatted_values() == (["name", "42"])


def test_metric_custom_parser() -> None:
    assert NamedPerson.parse(fields=["john doe", "42"]) == (
        NamedPerson(name=Name(first="john", last="doe"), age=42)
    )


def test_metric_custom_formatter() -> None:
    person = NamedPerson(name=Name(first="john", last="doe"), age=42)
    assert list(person.formatted_values()) == ["john doe", "42"]


def test_metric_parse_with_None() -> None:
    assert Person.parse(fields=["", "40"]) == Person(name=None, age=40)
    assert Person.parse(fields=["Sally", ""]) == Person(name="Sally", age=None)
    assert Person.parse(fields=["", ""]) == Person(name=None, age=None)


def test_metric_formatted_values_with_empty_string() -> None:
    assert Person(name=None, age=42).formatted_values() == (["", "42"])
    assert Person(name="Sally", age=None).formatted_values() == (["Sally", ""])
    assert Person(name=None, age=None).formatted_values() == (["", ""])


@attr.s(auto_attribs=True, frozen=True)
class ListPerson(Metric["ListPerson"]):
    name: List[Optional[str]]
    age: List[Optional[int]]


def test_metric_list_format() -> None:
    assert ListPerson(name=["Max", "Sally"], age=[43, 55]).formatted_values() == (
        ["Max,Sally", "43,55"]
    )


def test_metric_list_parse() -> None:
    assert ListPerson.parse(fields=["Max,Sally", "43, 55"]) == ListPerson(
        name=["Max", "Sally"], age=[43, 55]
    )


def test_metric_list_format_with_empty_string() -> None:
    assert ListPerson(name=[None, "Sally"], age=[43, 55]).formatted_values() == (
        [",Sally", "43,55"]
    )
    assert ListPerson(name=[None, "Sally"], age=[None, 55]).formatted_values() == (
        [",Sally", ",55"]
    )
    assert ListPerson(name=["Max", "Sally"], age=[None, None]).formatted_values() == (
        ["Max,Sally", ","]
    )


def test_metric_list_parse_with_None() -> None:
    assert ListPerson.parse(fields=[",Sally", "40, 30"]) == ListPerson(
        name=[None, "Sally"], age=[40, 30]
    )
    assert ListPerson.parse(fields=[",Sally", ", 30"]) == ListPerson(
        name=[None, "Sally"], age=[None, 30]
    )
    assert ListPerson.parse(fields=["Max,Sally", ","]) == ListPerson(
        name=["Max", "Sally"], age=[None, None]
    )
