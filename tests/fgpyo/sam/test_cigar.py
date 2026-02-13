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


###############################################################################
# Tests for Cigar truncation methods (ported from fgbio)
###############################################################################


@pytest.mark.parametrize(
    ("cigar_string", "length", "expected"),
    [
        # No truncation needed
        ("75M", 100, "75M"),
        # Actual truncation to length 50 with various element types M, I, D, N, S, H, P, EQ, X
        ("60M", 50, "50M"),
        ("60I", 50, "50I"),
        ("60D", 50, "60D"),  # no effect on query
        ("60N", 50, "60N"),  # no effect on query
        ("60S", 50, "50S"),
        ("60H", 50, "60H"),  # no effect on query
        ("60P", 50, "60P"),  # no effect on query
        ("60=", 50, "50="),
        ("60X", 50, "50X"),
        ("10H50M", 50, "10H50M"),  # Hard clips preserved
        ("25M10I25M", 50, "25M10I15M"),  # Insertions consume query
        ("25M10D25M", 50, "25M10D25M"),  # Deletions don't consume query
        ("50M10S", 50, "50M"),  # Trailing soft clips removed
        # Additional edge cases
        ("10M", 0, "*"),  # Truncate to zero
        ("*", 5, "*"),  # Empty CIGAR
        ("5H10M", 0, "*"),  # Length 0 and leading non-consuming elements
        ("10S10M", 0, "*"),
        ("100M", 1, "1M"),  # Element splitting
        ("100M", 50, "50M"),
        ("100M", 99, "99M"),
        ("10M10D10I10N10M", 5, "5M"),  # Interspersed non-consuming elements
        ("10M10D10I10N10M", 10, "10M"),
        ("10M10D10I10N10M", 15, "10M10D5I"),
        ("10M10D10I10N10M", 20, "10M10D10I"),
        ("10M10D10I10N10M", 25, "10M10D10I10N5M"),
        ("10M10D10I10N10M", 30, "10M10D10I10N10M"),
    ],
)
def test_truncate_to_query_length(cigar_string: str, length: int, expected: str) -> None:
    """truncate_to_query_length should return the expected truncated CIGAR."""
    cigar = Cigar.from_cigarstring(cigar_string)
    result = cigar.truncate_to_query_length(length)
    assert str(result) == expected
    assert result.length_on_query() == min(length, cigar.length_on_query())


@pytest.mark.parametrize(
    ("cigar_string", "length", "expected"),
    [
        # No truncation needed
        ("75M", 100, "75M"),
        # Actual truncation to length 50 with various element types M, I, D, N, S, H, P, EQ, X
        ("60M", 50, "50M"),
        ("60I", 50, "60I"),  # no effect on target
        ("60D", 50, "50D"),
        ("60N", 50, "50N"),
        ("60S", 50, "60S"),  # no effect on target
        ("60H", 50, "60H"),  # no effect on target
        ("60P", 50, "60P"),  # no effect on target
        ("60=", 50, "50="),
        ("60X", 50, "50X"),
        ("10H50M", 50, "10H50M"),  # Hard clips preserved
        ("25M10I25M", 50, "25M10I25M"),  # Insertions don't consume target
        ("25M10D25M", 50, "25M10D15M"),  # Deletions consume target
        ("50M10S", 50, "50M"),  # Trailing soft clips removed
        # Additional edge cases
        ("10M", 0, "*"),  # Truncate to zero
        ("*", 5, "*"),  # Empty CIGAR
        ("5H10M", 0, "*"),  # Length 0 and leading non-consuming elements
        ("10S10M", 0, "*"),
        ("100M", 1, "1M"),  # Element splitting
        ("100M", 50, "50M"),
        ("100M", 99, "99M"),
        ("10M10D10I10N10M", 5, "5M"),  # Interspersed non-consuming elements
        ("10M10D10I10N10M", 10, "10M"),
        ("10M10D10I10N10M", 15, "10M5D"),
        ("10M10D10I10N10M", 20, "10M10D"),
        ("10M10D10I10N10M", 25, "10M10D10I5N"),
        ("10M10D10I10N10M", 30, "10M10D10I10N"),
        ("10M10D10I10N10M", 35, "10M10D10I10N5M"),
        ("10M10D10I10N10M", 40, "10M10D10I10N10M"),
    ],
)
def test_truncate_to_target_length(cigar_string: str, length: int, expected: str) -> None:
    """truncate_to_target_length should return the expected truncated CIGAR."""
    cigar = Cigar.from_cigarstring(cigar_string)
    result = cigar.truncate_to_target_length(length)
    assert str(result) == expected
    assert result.length_on_target() == min(length, cigar.length_on_target())


def test_truncate_methods_return_new_cigar() -> None:
    """Truncate methods should return new Cigar objects, not modify original."""
    original = Cigar.from_cigarstring("10M5I10M")
    truncated = original.truncate_to_query_length(12)

    assert str(original) == "10M5I10M"  # Original unchanged
    assert str(truncated) == "10M2I"  # New cigar truncated
    assert original is not truncated  # Different objects
