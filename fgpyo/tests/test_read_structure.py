import pytest
from typing import Tuple
from fgpyo.read_structure import ReadStructure
from fgpyo.read_structure import ReadSegment
from fgpyo.read_structure import SegmentType


def _T(off: int, len: int) -> ReadSegment:
    return ReadSegment(offset=off, length=len, kind=SegmentType.Template)


def _B(off: int, len: int) -> ReadSegment:
    return ReadSegment(offset=off, length=len, kind=SegmentType.SampleBarcode)


def _M(off: int, len: int) -> ReadSegment:
    return ReadSegment(offset=off, length=len, kind=SegmentType.MolecularBarcode)


def _S(off: int, len: int) -> ReadSegment:
    return ReadSegment(offset=off, length=len, kind=SegmentType.Skip)


@pytest.mark.parametrize(
    "string,segments",
    [
        ("1T", (_T(0, 1),)),
        ("1B", (_B(0, 1),)),
        ("1M", (_M(0, 1),)),
        ("1S", (_S(0, 1),)),
        ("101T", (_T(0, 101),)),
        (
            "5B101T",
            (
                _B(0, 5),
                _T(5, 101),
            ),
        ),
        ("123456789T", (_T(0, 123456789),)),
        (
            "10T10B10B10S10M",
            (
                _T(0, 10),
                _B(10, 10),
                _B(20, 10),
                _S(30, 10),
                _M(40, 10),
            ),
        ),
    ],
)
def test_read_structure_from_string(string: str, segments: Tuple[ReadSegment, ...]) -> None:
    assert ReadStructure.from_string(segments=string).segments == segments


@pytest.mark.parametrize(
    "string,segments",
    [
        (
            "75T 8B 8B 75T",
            (
                _T(0, 75),
                _B(75, 8),
                _B(83, 8),
                _T(91, 75),
            ),
        ),
        (
            " 75T  8B   8B     75T  ",
            (
                _T(0, 75),
                _B(75, 8),
                _B(83, 8),
                _T(91, 75),
            ),
        ),
    ],
)
def test_read_structure_from_string_with_whitespace(
    string: str, segments: Tuple[ReadSegment, ...]
) -> None:
    assert ReadStructure.from_string(segments=string).segments == segments


# TODO: more tests
