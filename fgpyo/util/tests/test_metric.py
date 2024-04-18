# attr and dataclasses are both nightmares for type-checking, and trying to combine them both in
# an if-statement is a level of Hell that Dante never conceived of. Turning off mypy for this file:
# mypy: ignore-errors
import enum
import gzip
import sys
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from typing import TypeVar
from typing import Union

if sys.version_info >= (3, 12):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

import dataclasses

import attr
import pytest

from fgpyo.util.inspect import is_attr_class
from fgpyo.util.inspect import is_dataclasses_class
from fgpyo.util.metric import Metric


class EnumTest(enum.Enum):
    EnumVal1 = "val1"
    EnumVal2 = "val2"
    EnumVal3 = "val3"


T = TypeVar("T", bound=Type)


def make_dataclass(use_attr: bool = False) -> Callable[[T], T]:
    """Decorator to make a attr- or dataclasses-style dataclass"""
    sys.stderr.write(f"use_attr = {use_attr}\n")
    if use_attr:

        def make_attr(cls: T) -> T:
            return attr.s(auto_attribs=True, frozen=True)(cls)

        return make_attr
    else:

        def make_dataclasses(cls: T) -> T:
            return dataclasses.dataclass(frozen=True)(cls)

        return make_dataclasses


class DataBuilder:
    """
    Holds classes and data for testing, either using attr- or dataclasses-style dataclass
    We need to run each test both with attr and dataclasses classes, so use this class to construct
    the test metrics appropriately, governed by the use_attr flag. After construction, the
    DataBuilder object will have all the required Metrics:

    Attributes:
        use_attr: If True use attr classes for Metrics, if False use dataclasses
        DummyMetric: Metric with many different field types
        Person: Metric with optional name and age string fields
        Name: Metric with first and last name string fields and a parse method
        NameMetric: Metric to test specifying columns out of order
        NamedPerson: Metric with name (Name Metric) field and age (int) fields, and parsers.
        PersonMaybeAge = Person with required name string field and optional age int field
        PersonDefault = Person with required name string field and age int field with default value
        ListPerson = Person with list[str] name and list[int] age fields
        DUMMY_METRICS: a list of 3 different DummyMetrics
    """

    def __init__(self, use_attr: bool) -> None:
        self.use_attr = use_attr

        @make_dataclass(use_attr=use_attr)
        class DummyMetric(Metric["DummyMetric"]):
            int_value: int
            str_value: str
            bool_val: bool
            enum_val: EnumTest
            optional_str_value: Optional[str]
            optional_int_value: Optional[int]
            optional_bool_value: Optional[bool]
            optional_enum_value: Optional[EnumTest]
            dict_value: Dict[int, str]
            tuple_value: Tuple[int, str]
            list_value: List[str]
            complex_value: Dict[
                int,
                Dict[
                    Tuple[int, int],
                    Set[str],
                ],
            ]

        @make_dataclass(use_attr=use_attr)
        class Person(Metric["Person"]):
            name: Optional[str]
            age: Optional[int]

        @make_dataclass(use_attr=use_attr)
        class Name:
            first: str
            last: str

            @classmethod
            def parse(cls, value: str) -> "Name":
                fields = value.split(" ")
                return Name(first=fields[0], last=fields[1])

        @make_dataclass(use_attr=use_attr)
        class NameMetric(Metric["NameMetric"]):
            first: str
            last: str

        @make_dataclass(use_attr=use_attr)
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

        @make_dataclass(use_attr=use_attr)
        class PersonMaybeAge(Metric["PersonMaybeAge"]):
            name: str
            age: Optional[int]

        @make_dataclass(use_attr=use_attr)
        class PersonDefault(Metric["PersonDefault"]):
            name: str
            age: int = 0

        @make_dataclass(use_attr=use_attr)
        class ListPerson(Metric["ListPerson"]):
            name: List[Optional[str]]
            age: List[Optional[int]]

        self.DummyMetric = DummyMetric
        self.Person = Person
        self.Name = Name
        self.NameMetric = NameMetric
        self.NamedPerson = NamedPerson
        self.PersonMaybeAge = PersonMaybeAge
        self.PersonDefault = PersonDefault
        self.ListPerson = ListPerson

        self.DUMMY_METRICS: List[DummyMetric] = [
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
                complex_value={1: {(5, 1): {"mapped_test_val1", "setval2"}}},
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
                complex_value={2: {(-5, 1): {"mapped_test_val2", "setval2"}}},
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
                complex_value={3: {(8, 1): {"mapped_test_val3", "setval2"}}},
            ),
        ]


# construct the attr and dataclasses DataBuilder objects
attr_data_and_classes = DataBuilder(use_attr=True)
dataclasses_data_and_classes = DataBuilder(use_attr=False)

# get helper type and helper num_metrics that will be used frequently in tests
AnyDummyMetric = Union[attr_data_and_classes.DummyMetric, dataclasses_data_and_classes.DummyMetric]
num_metrics = len(attr_data_and_classes.DUMMY_METRICS)


@pytest.mark.parametrize("use_attr", [False, True])
def test_is_correct_dataclass_type(use_attr: bool) -> None:
    """
    Test that the DataBuilder class works as expected, as do the is_attr_class and
    is_dataclasses_class methods
    """
    data_and_classes = DataBuilder(use_attr=use_attr)
    assert use_attr == data_and_classes.use_attr
    assert is_attr_class(data_and_classes.DummyMetric) is use_attr
    assert is_dataclasses_class(data_and_classes.DummyMetric) is not use_attr
    assert is_attr_class(data_and_classes.Person) is use_attr
    assert is_dataclasses_class(data_and_classes.Person) is not use_attr
    assert is_attr_class(data_and_classes.Name) is use_attr
    assert is_dataclasses_class(data_and_classes.Name) is not use_attr
    assert is_attr_class(data_and_classes.NameMetric) is use_attr
    assert is_dataclasses_class(data_and_classes.NameMetric) is not use_attr
    assert is_attr_class(data_and_classes.NamedPerson) is use_attr
    assert is_dataclasses_class(data_and_classes.NamedPerson) is not use_attr
    assert is_attr_class(data_and_classes.PersonMaybeAge) is use_attr
    assert is_dataclasses_class(data_and_classes.PersonMaybeAge) is not use_attr
    assert is_attr_class(data_and_classes.PersonDefault) is use_attr
    assert is_dataclasses_class(data_and_classes.PersonDefault) is not use_attr
    assert len(data_and_classes.DUMMY_METRICS) == num_metrics


def pytest_generate_tests(metafunc: Any) -> None:
    if "DummyMetric" in metafunc.fixturenames:
        metafunc.parametrize(
            "DummyMetric",
            [attr_data_and_classes.DummyMetric, dataclasses_data_and_classes.DummyMetric],
        )
    if "DUMMY_METRICS" in metafunc.fixturenames:
        metafunc.parametrize(
            "DUMMY_METRICS",
            [attr_data_and_classes.DUMMY_METRICS, dataclasses_data_and_classes.DUMMY_METRICS],
        )


@pytest.fixture(scope="function")
def metric(request, data_and_classes: DataBuilder) -> AnyDummyMetric:
    yield data_and_classes.DUMMY_METRICS[request.param]


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
@pytest.mark.parametrize("metric", range(num_metrics), indirect=True)
def test_metric_roundtrip(
    tmp_path: Path,
    data_and_classes: DataBuilder,
    metric: AnyDummyMetric,
) -> None:
    path: Path = tmp_path / "metrics.txt"
    DummyMetric: TypeAlias = data_and_classes.DummyMetric

    DummyMetric.write(path, metric)
    metrics: List[DummyMetric] = list(DummyMetric.read(path=path))

    assert len(metrics) == 1
    assert metrics[0] == metric


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metrics_roundtrip(tmp_path: Path, data_and_classes: DataBuilder) -> None:
    path: Path = tmp_path / "metrics.txt"
    DummyMetric: TypeAlias = data_and_classes.DummyMetric

    DummyMetric.write(path, *data_and_classes.DUMMY_METRICS)
    metrics: List[DummyMetric] = list(DummyMetric.read(path=path))

    assert len(metrics) == len(data_and_classes.DUMMY_METRICS)
    assert metrics == data_and_classes.DUMMY_METRICS


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metrics_roundtrip_gzip(tmp_path: Path, data_and_classes: DataBuilder) -> None:
    path: Path = Path(tmp_path) / "metrics.txt.gz"
    DummyMetric: Type[Metric] = data_and_classes.DummyMetric

    DummyMetric.write(path, *data_and_classes.DUMMY_METRICS)

    with gzip.open(path, "r") as handle:
        handle.read(1)  # Will raise an exception if not a GZIP file.

    metrics: List[DummyMetric] = list(DummyMetric.read(path=path))

    assert len(metrics) == len(data_and_classes.DUMMY_METRICS)
    assert metrics == data_and_classes.DUMMY_METRICS


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metrics_read_extra_columns(tmp_path: Path, data_and_classes: DataBuilder) -> None:
    Person: TypeAlias = data_and_classes.Person
    person = Person(name="Max", age=42)
    path = tmp_path / "metrics.txt"
    with path.open("w") as writer:
        header = Person.header()
        header.append("foo")
        writer.write("\t".join(header) + "\n")
        writer.write(f"{person.name}\t{person.age}\tbar\n")

    assert list(Person.read(path=path)) == [person]
    assert list(Person.read(path=path, ignore_extra_fields=True)) == [person]
    with pytest.raises(ValueError):
        list(Person.read(path=path, ignore_extra_fields=False))


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metrics_read_missing_optional_columns(
    tmp_path: Path, data_and_classes: DataBuilder
) -> None:
    PersonMaybeAge: TypeAlias = data_and_classes.PersonMaybeAge
    person = PersonMaybeAge(name="Max", age=None)
    path = tmp_path / "metrics.txt"

    # The "age" column is optional, and not in the file, but that's ok
    with path.open("w") as writer:
        writer.write("name\nMax\n")
    assert list(PersonMaybeAge.read(path=path)) == [person]

    # The "age" column is not optional, and not in the file on line 3, and that's not ok
    with path.open("w") as writer:
        writer.write("name\tage\nMax\t42\nMax\n")
    with pytest.raises(ValueError):
        list(PersonMaybeAge.read(path=path))


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_read_missing_column_with_default(
    tmp_path: Path, data_and_classes: DataBuilder
) -> None:
    PersonDefault: TypeAlias = data_and_classes.PersonDefault
    person = PersonDefault(name="Max")
    path = tmp_path / "metrics.txt"

    # The "age" column hs a default, and not in the file, but that's ok
    with path.open("w") as writer:
        writer.write("name\nMax\n")
    assert list(PersonDefault.read(path=path)) == [person]

    # All fields specified
    with path.open("w") as writer:
        writer.write("name\tage\nMax\t42\n")
    assert list(PersonDefault.read(path=path)) == [PersonDefault(name="Max", age=42)]

    # Just age specified, but not the required name column!
    with path.open("w") as writer:
        writer.write("age\n42\n")
    with pytest.raises(ValueError):
        list(PersonDefault.read(path=path))


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_header(data_and_classes: DataBuilder) -> None:
    assert data_and_classes.DummyMetric.header() == [
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


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_values(data_and_classes: DataBuilder) -> None:
    assert list(data_and_classes.Person(name="name", age=42).values()) == ["name", 42]


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_parse(data_and_classes: DataBuilder) -> None:
    Person: TypeAlias = data_and_classes.Person
    assert Person.parse(fields=["name", "42"]) == Person(name="name", age=42)


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_formatted_values(data_and_classes: DataBuilder) -> None:
    assert data_and_classes.Person(name="name", age=42).formatted_values() == (["name", "42"])


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_custom_parser(data_and_classes: DataBuilder) -> None:
    NamedPerson: TypeAlias = data_and_classes.NamedPerson
    assert NamedPerson.parse(fields=["john doe", "42"]) == (
        NamedPerson(name=data_and_classes.Name(first="john", last="doe"), age=42)
    )


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_custom_formatter(data_and_classes: DataBuilder) -> None:
    person = data_and_classes.NamedPerson(
        name=data_and_classes.Name(first="john", last="doe"), age=42
    )
    assert list(person.formatted_values()) == ["john doe", "42"]


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_parse_with_none(data_and_classes: DataBuilder) -> None:
    Person: TypeAlias = data_and_classes.Person
    assert Person.parse(fields=["", "40"]) == Person(name=None, age=40)
    assert Person.parse(fields=["Sally", ""]) == Person(name="Sally", age=None)
    assert Person.parse(fields=["", ""]) == Person(name=None, age=None)


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_formatted_values_with_empty_string(data_and_classes: DataBuilder) -> None:
    Person: TypeAlias = data_and_classes.Person
    assert Person(name=None, age=42).formatted_values() == (["", "42"])
    assert Person(name="Sally", age=None).formatted_values() == (["Sally", ""])
    assert Person(name=None, age=None).formatted_values() == (["", ""])


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_list_format(data_and_classes: DataBuilder) -> None:
    assert data_and_classes.ListPerson(name=["Max", "Sally"], age=[43, 55]).formatted_values() == (
        ["Max,Sally", "43,55"]
    )


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_list_parse(data_and_classes: DataBuilder) -> None:
    ListPerson: TypeAlias = data_and_classes.ListPerson
    assert ListPerson.parse(fields=["Max,Sally", "43, 55"]) == ListPerson(
        name=["Max", "Sally"], age=[43, 55]
    )


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_list_format_with_empty_string(data_and_classes: DataBuilder) -> None:
    ListPerson: TypeAlias = data_and_classes.ListPerson
    assert ListPerson(name=[None, "Sally"], age=[43, 55]).formatted_values() == (
        [",Sally", "43,55"]
    )
    assert ListPerson(name=[None, "Sally"], age=[None, 55]).formatted_values() == (
        [",Sally", ",55"]
    )
    assert ListPerson(name=["Max", "Sally"], age=[None, None]).formatted_values() == (
        ["Max,Sally", ","]
    )


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_list_parse_with_none(data_and_classes: DataBuilder) -> None:
    ListPerson: TypeAlias = data_and_classes.ListPerson
    assert ListPerson.parse(fields=[",Sally", "40, 30"]) == ListPerson(
        name=[None, "Sally"], age=[40, 30]
    )
    assert ListPerson.parse(fields=[",Sally", ", 30"]) == ListPerson(
        name=[None, "Sally"], age=[None, 30]
    )
    assert ListPerson.parse(fields=["Max,Sally", ","]) == ListPerson(
        name=["Max", "Sally"], age=[None, None]
    )


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metrics_fast_concat(tmp_path: Path, data_and_classes: DataBuilder) -> None:
    path_input = [
        tmp_path / "metrics_1.txt",
        tmp_path / "metrics_2.txt",
        tmp_path / "metrics_3.txt",
    ]
    path_output: Path = tmp_path / "metrics_concat.txt"
    DummyMetric: TypeAlias = data_and_classes.DummyMetric
    DUMMY_METRICS: list[DummyMetric] = data_and_classes.DUMMY_METRICS

    DummyMetric.write(path_input[0], DUMMY_METRICS[0])
    DummyMetric.write(path_input[1], DUMMY_METRICS[1])
    DummyMetric.write(path_input[2], DUMMY_METRICS[2])

    Metric.fast_concat(*path_input, output=path_output)
    metrics: List[DummyMetric] = list(DummyMetric.read(path=path_output))

    assert len(metrics) == len(DUMMY_METRICS)
    assert metrics[0].header() == DummyMetric.header()
    assert metrics[1].header() == DummyMetric.header()
    assert metrics[2].header() == DummyMetric.header()
    assert metrics[0] == DUMMY_METRICS[0]
    assert metrics[1] == DUMMY_METRICS[1]
    assert metrics[2] == DUMMY_METRICS[2]


@pytest.mark.parametrize("data_and_classes", (attr_data_and_classes, dataclasses_data_and_classes))
def test_metric_columns_out_of_order(tmp_path: Path, data_and_classes: DataBuilder) -> None:
    path = tmp_path / "metrics.txt"
    NameMetric: TypeAlias = data_and_classes.NameMetric

    name = NameMetric(first="jon", last="Doe")

    # Write the columns out of order (last then first)
    with path.open("w") as writer:
        writer.write("last\tfirst\n")
        writer.write(f"{name.last}\t{name.first}\n")

    names = list(NameMetric.read(path=path))
    assert len(names) == 1
    assert names[0] == name
