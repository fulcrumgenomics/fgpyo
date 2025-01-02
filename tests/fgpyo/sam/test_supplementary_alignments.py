import pytest

from fgpyo.sam import Cigar
from fgpyo.sam import SupplementaryAlignment
from fgpyo.sam.builder import SamBuilder


def test_supplementary_alignment() -> None:
    # reverse
    assert SupplementaryAlignment.from_tag_item(
        "chr1,123,-,100M50S,60,4"
    ) == SupplementaryAlignment(
        reference_name="chr1",
        reference_start=122,
        is_forward=False,
        cigar=Cigar.from_cigarstring("100M50S"),
        mapq=60,
        edit_distance=4,
    )

    # forward
    assert SupplementaryAlignment.from_tag_item(
        "chr1,123,+,50S100M,60,0"
    ) == SupplementaryAlignment(
        reference_name="chr1",
        reference_start=122,
        is_forward=True,
        cigar=Cigar.from_cigarstring("50S100M"),
        mapq=60,
        edit_distance=0,
    )

    # not enough fields
    with pytest.raises(ValueError, match="SA tag item does not have 6 ',' separated fields"):
        SupplementaryAlignment.from_tag_item("chr1,123,+,50S100M,60")


def test_many_from_tag() -> None:
    assert SupplementaryAlignment.many_from_tag("") == []
    assert SupplementaryAlignment.many_from_tag(";") == []

    s1 = "chr1,123,+,50S100M,60,0"
    s2 = "chr2,456,-,75S75M,60,1"
    sa1 = SupplementaryAlignment("chr1", 122, True, Cigar.from_cigarstring("50S100M"), 60, 0)
    sa2 = SupplementaryAlignment("chr2", 455, False, Cigar.from_cigarstring("75S75M"), 60, 1)

    assert SupplementaryAlignment.many_from_tag(f"{s1};") == [sa1]
    assert SupplementaryAlignment.many_from_tag(f"{s2};") == [sa2]
    assert SupplementaryAlignment.many_from_tag(f"{s1};{s2};") == [sa1, sa2]


def test_format_supplementary_alignment() -> None:
    for sa_string in ["chr1,123,-,100M50S,60,4", "chr1,123,+,100M50S,60,3"]:
        sa = SupplementaryAlignment.from_tag_item(sa_string)
        assert str(sa) == sa_string


def test_many_from_primary() -> None:
    """Test that we can construct a SupplementaryAlignment from an AlignedSegment."""

    builder = SamBuilder()

    read = builder.add_single()
    assert SupplementaryAlignment.many_from_primary(read) == []

    s1 = "chr1,123,+,50S100M,60,0"
    s2 = "chr2,456,-,75S75M,60,1"
    sa1 = SupplementaryAlignment("chr1", 122, True, Cigar.from_cigarstring("50S100M"), 60, 0)
    sa2 = SupplementaryAlignment("chr2", 455, False, Cigar.from_cigarstring("75S75M"), 60, 1)

    read = builder.add_single(attrs={"SA": f"{s1};"})
    assert SupplementaryAlignment.many_from_primary(read) == [sa1]

    read = builder.add_single(attrs={"SA": f"{s1};{s2};"})
    assert SupplementaryAlignment.many_from_primary(read) == [sa1, sa2]


def test_end() -> None:
    """Test that we can get the end of a SupplementaryAlignment."""

    s1 = SupplementaryAlignment.from_tag_item("chr1,123,+,50S100M,60,0")

    # NB: the SA tag is one-based, but SupplementaryAlignment is zero-based
    assert s1.reference_end == 222
