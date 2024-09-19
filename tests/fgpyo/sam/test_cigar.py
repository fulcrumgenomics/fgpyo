from typing import Optional

import pytest

from fgpyo.sam import Cigar

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
        ("10M", range(0, 10)),
        ("10M10I", range(0, 20)),
        ("10X10I", range(0, 20)),
        ("10X10D", range(0, 10)),
        ("10=10D", range(0, 10)),
        ("10S10M", range(10, 20)),
        ("10H10M", range(0, 10)),
        ("10H10S10M", range(10, 20)),
        ("10H10S10M5S", range(10, 20)),
        ("10H10S10M5S10H", range(10, 20)),
        ("10H", None),
        ("10S", None),
        ("10S10H", None),
        ("5H10S10H", None),
        ("76D", None),
        ("76I", range(0, 76)),
        ("10P76S", None),
        ("50S1000N50S", None),
    },
)
def test_get_alignments(cigar_string: str, maybe_range: Optional[range]) -> None:
    cig = Cigar.from_cigarstring(cigar_string)
    assert Cigar.get_query_alignment_offsets(cig, reverse=False) == maybe_range


@pytest.mark.parametrize(
    ("cigar_string", "maybe_range"),
    {
        ("10M", range(0, 10)),
        ("10M10I", range(0, 20)),
        ("10X10I", range(0, 20)),
        ("10X10D", range(0, 10)),
        ("10=10D", range(0, 10)),
        ("10S10M", range(0, 10)),
        ("10H10M", range(0, 10)),
        ("10H10S10M", range(0, 10)),
        ("10H10S10M5S", range(5, 15)),
        ("10H10S10M5S10H", range(5, 15)),
        ("10H", None),
        ("10S", None),
        ("10S10H", None),
        ("5H10S10H", None),
    },
)
def test_get_alignments_reversed(cigar_string: str, maybe_range: Optional[range]) -> None:
    cig = Cigar.from_cigarstring(cigar_string)
    assert Cigar.get_query_alignment_offsets(cig, reverse=True) == maybe_range
