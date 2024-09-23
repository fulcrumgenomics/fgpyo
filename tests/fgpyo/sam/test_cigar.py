from typing import Optional
from typing import Tuple

import pytest

from fgpyo.sam import Cigar
from fgpyo.sam import RangeOfBases

cigar = Cigar.from_cigarstring("1M4D45N37X23I11=")


@pytest.mark.parametrize("index", range(-len(cigar.elements), len(cigar.elements)))
def test_direct_access(index: int) -> None:
    assert cigar[index] == cigar.elements[index]
    assert cigar[index:] == cigar.elements[index:]
    assert cigar[:index] == cigar.elements[:index]
    assert cigar[index:-1] == cigar.elements[index:-1]


@pytest.mark.parametrize(
    "index",
    [
        -7,
        -100,
        6,
        100,
    ],
)
def test_bad_index_raises_index_error(index: int) -> None:
    with pytest.raises(IndexError):
        cigar[index]


@pytest.mark.parametrize("index", ["a", "b", (1, 2)])
def test_bad_index_raises_type_error(index: int) -> None:
    with pytest.raises(TypeError):
        cigar[index]


@pytest.mark.parametrize(
    ("cigar_string", "maybe_range"),
    {
        ("10M", RangeOfBases(0, 10)),
        ("10M10I", RangeOfBases(0, 20)),
        ("10X10I", RangeOfBases(0, 20)),
        ("10X10D", RangeOfBases(0, 10)),
        ("10=10D", RangeOfBases(0, 10)),
        ("10S10M", RangeOfBases(10, 20)),
        ("10H10M", RangeOfBases(0, 10)),
        ("10H10S10M", RangeOfBases(10, 20)),
        ("10H10S10M5S", RangeOfBases(10, 20)),
        ("10H10S10M5S10H", RangeOfBases(10, 20)),
        ("10H", None),
        ("10S", None),
        ("10S10H", None),
        ("5H10S10H", None),
        ("76D", None),
        ("76I", RangeOfBases(0, 76)),
        ("10P76S", None),
        ("50S1000N50S", None),
    },
)
def test_get_alignments(cigar_string: str, maybe_range: Optional[RangeOfBases]) -> None:
    cig = Cigar.from_cigarstring(cigar_string)

    assert Cigar.query_alignment_offsets(cig, reverse=False) == maybe_range


@pytest.mark.parametrize(
    ("cigar_string", "maybe_range"),
    {
        ("10M", RangeOfBases(0, 10)),
        ("10M10I", RangeOfBases(0, 20)),
        ("10X10I", RangeOfBases(0, 20)),
        ("10X10D", RangeOfBases(0, 10)),
        ("10=10D", RangeOfBases(0, 10)),
        ("10S10M", RangeOfBases(0, 10)),
        ("10H10M", RangeOfBases(0, 10)),
        ("10H10S10M", RangeOfBases(0, 10)),
        ("10H10S10M5S", RangeOfBases(5, 15)),
        ("10H10S10M5S10H", RangeOfBases(5, 15)),
        ("10H", None),
        ("10S", None),
        ("10S10H", None),
        ("5H10S10H", None),
    },
)
def test_get_alignments_reversed(cigar_string: str, maybe_range: Optional[Tuple[int, int]]) -> None:
    cig = Cigar.from_cigarstring(cigar_string)

    assert Cigar.query_alignment_offsets(cig, reverse=True) == maybe_range
    if maybe_range is not None:
        start, stop = maybe_range
