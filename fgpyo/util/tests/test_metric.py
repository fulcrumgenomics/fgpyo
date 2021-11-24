from pathlib import Path
from typing import Dict
from typing import Tuple
from typing import List
from typing import Set

import enum
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
        dict_value={},
        tuple_value=(2, "test3"),
        list_value=["1", "2", "3"],
        complex_value={3: {(8, 1): set({"mapped_test_val3", "setval2"})}},
    ),
]


@pytest.mark.parametrize("metric", DUMMY_METRICS)
def test_metric_roundtrip(tmpdir: TmpDir, metric: DummyMetric) -> None:
    path: Path = Path(tmpdir) / "metrics.txt"

    DummyMetric.write(path, metric)
    metrics: List[DummyMetric] = DummyMetric.read(path=path)

    with path.open("r") as reader:
        for line in reader:
            print(line)

    assert len(metrics) == 1
    assert metrics[0] == metric


def test_metrics_roundtrip(tmpdir: TmpDir) -> None:
    path: Path = Path(tmpdir) / "metrics.txt"

    DummyMetric.write(path, *DUMMY_METRICS)
    metrics: List[DummyMetric] = DummyMetric.read(path=path)

    with path.open("r") as reader:
        for line in reader:
            print(line)

    assert len(metrics) == len(DUMMY_METRICS)
    assert metrics == DUMMY_METRICS
