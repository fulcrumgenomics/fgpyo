from typing import Tuple

import pytest

from fgpyo.sam import Cigar

cigar = Cigar.from_cigarstring("1M4D45N37X23I11=")


@pytest.mark.parametrize(
    ("cigar_string", "expected_range"),
    [
        ("10M", (0, 10)),
        ("10M10I", (0, 20)),
        ("10X10I", (0, 20)),
        ("10X10D", (0, 10)),
        ("10=10D", (0, 10)),
        ("10S10M", (10, 20)),
        ("10H10M", (0, 10)),
        ("10H10S10M", (10, 20)),
        ("10H10S10M5S", (10, 20)),
        ("10H10S10M5S10H", (10, 20)),
        ("76I", (0, 76)),
    ],
)
def test_query_alignment_offsets(cigar_string: str, expected_range: Tuple[int, int]) -> None:
    """
    cig.query_alignment_offsets() should return the expected results.
    """
    cig = Cigar.from_cigarstring(cigar_string)
    ret = cig.query_alignment_offsets()
    assert ret == expected_range


@pytest.mark.parametrize(
    ("cigar_string"),
    [
        ("10H"),
        ("10S"),
        ("10S10H"),
        ("5H10S10H"),
        ("76D"),
        ("10P76S"),
        ("50S1000N50S"),
    ],
)
def test_query_alignment_offsets_failures(cigar_string: str) -> None:
    """query_alignment_offsets() should raise a ValueError if the CIGAR has no aligned positions."""
    cig = Cigar.from_cigarstring(cigar_string)
    with pytest.raises(ValueError):
        cig.query_alignment_offsets()

    with pytest.raises(ValueError):
        cig.reversed().query_alignment_offsets()


@pytest.mark.parametrize(
    ("cigar_string", "expected_range"),
    [
        ("10M", (0, 10)),
        ("10M10I", (0, 20)),
        ("10X10I", (0, 20)),
        ("10X10D", (0, 10)),
        ("10=10D", (0, 10)),
        ("10S10M", (0, 10)),
        ("10H10M", (0, 10)),
        ("10H10S10M", (0, 10)),
        ("10H10S10M5S", (5, 15)),
        ("10H10S10M5S10H", (5, 15)),
    ],
)
def test_query_alignment_offsets_reversed(
    cigar_string: str, expected_range: Tuple[int, int]
) -> None:
    """
    cig.revered().query_alignment_offsets() should return the expected results.
    """
    cig = Cigar.from_cigarstring(cigar_string)

    ret = cig.reversed().query_alignment_offsets()
    assert ret == expected_range
