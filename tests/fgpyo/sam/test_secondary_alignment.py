from typing import Any

import pytest

from fgpyo.sam import NO_QUERY_BASES
from fgpyo.sam import Cigar
from fgpyo.sam import SecondaryAlignment
from fgpyo.sam import Template
from fgpyo.sam import sum_of_base_qualities
from fgpyo.sam.builder import SamBuilder
from fgpyo.sequence import reverse_complement


@pytest.mark.parametrize(
    ["kwargs", "error"],
    [
        (
            {
                "reference_name": "chr9",
                "reference_start": -1,
                "is_forward": False,
                "cigar": Cigar.from_cigarstring("49M"),
                "edit_distance": 4,
                "alignment_score": 0,
                "mapq": 30,
            },
            "Start cannot be less zero! Found: -1",
        ),
        (
            {
                "reference_name": "chr9",
                "reference_start": 123232,
                "is_forward": False,
                "cigar": Cigar.from_cigarstring("49M"),
                "edit_distance": -1,
                "alignment_score": 0,
                "mapq": 30,
            },
            "Edit distance cannot be less zero! Found: -1",
        ),
        (
            {
                "reference_name": "chr9",
                "reference_start": 123232,
                "is_forward": False,
                "cigar": Cigar.from_cigarstring("49M"),
                "edit_distance": 4,
                "alignment_score": -1,
                "mapq": 30,
            },
            "Alignment score cannot be less zero! Found: -1",
        ),
        (
            {
                "reference_name": "chr9",
                "reference_start": 123232,
                "is_forward": False,
                "cigar": Cigar.from_cigarstring("49M"),
                "edit_distance": 4,
                "alignment_score": 4,
                "mapq": -1,
            },
            "Mapping quality cannot be less zero! Found: -1",
        ),
    ],
)
def test_secondary_alignment_validation(kwargs: dict[str, Any], error: str) -> None:
    """Test that we raise exceptions for invalid arguments to SecondaryAlignment."""
    with pytest.raises(ValueError, match=error):
        SecondaryAlignment(**kwargs)


@pytest.mark.parametrize(
    ["part", "expected"],
    [
        [
            # Test a well-formed negatively stranded XB
            "chr9,-104599381,49M,4,0,30",
            SecondaryAlignment(
                reference_name="chr9",
                reference_start=104599380,
                is_forward=False,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=0,
                mapq=30,
            ),
        ],
        [
            # Test a positive stranded XB and extra trailing commas
            "chr3,+170653467,49M,4,0,20,,,,",
            SecondaryAlignment(
                reference_name="chr3",
                reference_start=170653466,
                is_forward=True,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=0,
                mapq=20,
            ),
        ],
        [
            # Test a well-formed negatively stranded XA
            "chr9,-104599381,49M,4",
            SecondaryAlignment(
                reference_name="chr9",
                reference_start=104599380,
                is_forward=False,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=None,
                mapq=None,
            ),
        ],
        [
            # Test a positive stranded XA and extra trailing commas
            "chr3,+170653467,49M,4,,,,",
            SecondaryAlignment(
                reference_name="chr3",
                reference_start=170653466,
                is_forward=True,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=None,
                mapq=None,
            ),
        ],
    ],
)
def test_secondary_alignment_from_part(part: str, expected: SecondaryAlignment) -> None:
    """Test that we can build an XA or XB from a part of the tag value."""
    assert SecondaryAlignment.from_tag_part(part) == expected


def test_many_from_tag_invalid_number_of_commas() -> None:
    """Test that we raise an exception if we don't have 6 or 8 fields."""
    with pytest.raises(
        ValueError, match="XA or XB tag part does not have 4 or 6 ',' separated fields:"
    ):
        SecondaryAlignment.from_tag_part("chr9,-104599381,49M")


@pytest.mark.parametrize(["stranded_start"], [["!1"], ["1"]])
def test_many_from_tag_raises_for_invalid_stranded_start(stranded_start: str) -> None:
    """Test that we raise an exception when stranded start is malformed."""
    with pytest.raises(
        ValueError, match=f"The stranded start field is malformed: {stranded_start}"
    ):
        SecondaryAlignment.from_tag_part(f"chr3,{stranded_start},49M,4")


@pytest.mark.parametrize(
    ["secondary", "expected"],
    [
        (
            SecondaryAlignment(
                reference_name="chr3",
                reference_start=170653466,
                is_forward=True,
                cigar=Cigar.from_cigarstring("1H49M"),
                edit_distance=4,
            ),
            170653466 + 49,
        ),
        (
            SecondaryAlignment(
                reference_name="chr3",
                reference_start=170653466,
                is_forward=True,
                cigar=Cigar.from_cigarstring("10M10I10D10M"),
                edit_distance=4,
            ),
            170653466 + 30,
        ),
    ],
)
def test_secondary_alignment_reference_end_property(
    secondary: SecondaryAlignment, expected: int
) -> None:
    """Test that we correctly calculate reference end based on start and cigar."""
    assert secondary.reference_end == expected


def test_xas_many_from_tag() -> None:
    """Test that we can build many secondary alignments from multiple parts in an XA tag value."""
    value: str = "chr9,-104599381,49M,4;chr3,+170653467,49M,4;;;"  # with trailing ';'
    assert SecondaryAlignment.many_from_tag(value) == [
        SecondaryAlignment(
            reference_name="chr9",
            reference_start=104599380,
            is_forward=False,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapq=None,
        ),
        SecondaryAlignment(
            reference_name="chr3",
            reference_start=170653466,
            is_forward=True,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapq=None,
        ),
    ]


def test_xbs_many_from_tag() -> None:
    """Test that we can build many secondary alignments from multiple parts in an XB tag value."""
    value: str = "chr9,-104599381,49M,4,0,30;chr3,+170653467,49M,4,0,20;;;"  # with trailing ';'
    assert SecondaryAlignment.many_from_tag(value) == [
        SecondaryAlignment(
            reference_name="chr9",
            reference_start=104599380,
            is_forward=False,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=0,
            mapq=30,
        ),
        SecondaryAlignment(
            reference_name="chr3",
            reference_start=170653466,
            is_forward=True,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=0,
            mapq=20,
        ),
    ]


def test_many_from_rec_returns_no_secondaries_when_unmapped() -> None:
    """Test that many_from_rec returns no secondaries when unmapped."""
    builder = SamBuilder()
    rec = builder.add_single()
    assert rec.is_unmapped
    assert len(list(SecondaryAlignment.many_sam_from_rec(rec))) == 0


def test_xa_many_from_rec() -> None:
    """Test that we return secondary alignments from a SAM record with multiple XAs."""
    value: str = "chr9,-104599381,49M,4;chr3,+170653467,49M,4;;;"  # with trailing ';'
    builder = SamBuilder()
    rec = builder.add_single(chrom="chr1", start=32)

    assert list(SecondaryAlignment.many_from_rec(rec)) == []

    rec.set_tag("XA", value)

    assert list(SecondaryAlignment.many_from_rec(rec)) == [
        SecondaryAlignment(
            reference_name="chr9",
            reference_start=104599380,
            is_forward=False,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapq=None,
        ),
        SecondaryAlignment(
            reference_name="chr3",
            reference_start=170653466,
            is_forward=True,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapq=None,
        ),
    ]


def test_xb_many_from_rec() -> None:
    """Test that we return secondary alignments from a SAM record with multiple XBs."""
    value: str = "chr9,-104599381,49M,4,0,30;chr3,+170653467,49M,4,0,20;;;"  # with trailing ';'
    builder = SamBuilder()
    rec = builder.add_single(chrom="chr1", start=32)

    assert list(SecondaryAlignment.many_from_rec(rec)) == []

    rec.set_tag("XB", value)

    assert list(SecondaryAlignment.many_from_rec(rec)) == [
        SecondaryAlignment(
            reference_name="chr9",
            reference_start=104599380,
            is_forward=False,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=0,
            mapq=30,
        ),
        SecondaryAlignment(
            reference_name="chr3",
            reference_start=170653466,
            is_forward=True,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=0,
            mapq=20,
        ),
    ]


def test_xa_many_sam_from_rec() -> None:
    """Test that we return secondary alignments as SAM records from a record with multiple XAs."""
    value: str = "chr9,-104599381,49M,4;chr3,+170653467,49M,4;;;"  # with trailing ';'
    builder = SamBuilder()
    rec, mate = builder.add_pair(chrom="chr1", start1=32, start2=49)
    rec.set_tag("RX", "ACGT")

    assert rec.query_sequence is not None  # for type narrowing
    assert rec.query_qualities is not None  # for type narrowing
    assert list(SecondaryAlignment.many_from_rec(rec)) == []

    rec.set_tag("XB", value)
    first, second = list(SecondaryAlignment.many_sam_from_rec(rec))

    assert first.reference_name == "chr9"
    assert first.reference_id == rec.header.get_tid("chr9")
    assert first.reference_start == 104599380
    assert not first.is_forward
    assert first.query_sequence == reverse_complement(rec.query_sequence)
    assert first.query_qualities == rec.query_qualities[::-1]
    assert first.cigarstring == "49M"
    assert not first.has_tag("AS")
    assert first.get_tag("NM") == 4
    assert first.get_tag("rh") == 1
    assert first.mapping_quality == 0

    assert second.reference_name == "chr3"
    assert second.reference_id == rec.header.get_tid("chr3")
    assert second.reference_start == 170653466
    assert second.is_forward
    assert second.query_sequence == rec.query_sequence
    assert second.query_qualities == rec.query_qualities
    assert second.cigarstring == "49M"
    assert not second.has_tag("AS")
    assert second.get_tag("NM") == 4
    assert second.get_tag("rh") == 1
    assert second.mapping_quality == 0

    for result in (first, second):
        assert result.query_name == rec.query_name
        assert result.is_read1 is rec.is_read1
        assert result.is_read2 is rec.is_read2
        assert result.is_duplicate is rec.is_duplicate
        assert result.is_paired is rec.is_paired
        assert not result.is_proper_pair
        assert result.is_qcfail is rec.is_qcfail
        assert result.is_secondary
        assert not result.is_supplementary
        assert result.is_mapped

        assert result.next_reference_id == mate.reference_id
        assert result.next_reference_name == mate.reference_name
        assert result.next_reference_start == mate.reference_start
        assert result.mate_is_mapped is mate.is_mapped
        assert result.mate_is_reverse is mate.is_reverse
        assert result.get_tag("MC") == mate.cigarstring
        assert result.get_tag("ms") == sum_of_base_qualities(mate)
        assert result.get_tag("MQ") == mate.mapping_quality
        assert result.get_tag("RG") == rec.get_tag("RG")
        assert result.get_tag("RX") == rec.get_tag("RX")


def test_xb_many_sam_from_rec() -> None:
    """Test that we return secondary alignments as SAM records from a record with multiple XBs."""
    value: str = "chr9,-104599381,49M,4,0,30;chr3,+170653467,49M,4,0,20;;;"  # with trailing ';'
    builder = SamBuilder()
    rec, mate = builder.add_pair(chrom="chr1", start1=32, start2=49)
    rec.set_tag("RX", "ACGT")

    assert rec.query_sequence is not None  # for type narrowing
    assert rec.query_qualities is not None  # for type narrowing
    assert list(SecondaryAlignment.many_from_rec(rec)) == []

    rec.set_tag("XB", value)
    first, second = list(SecondaryAlignment.many_sam_from_rec(rec))

    assert first.reference_name == "chr9"
    assert first.reference_id == rec.header.get_tid("chr9")
    assert first.reference_start == 104599380
    assert not first.is_forward
    assert first.query_sequence == reverse_complement(rec.query_sequence)
    assert first.query_qualities == rec.query_qualities[::-1]
    assert first.cigarstring == "49M"
    assert first.get_tag("AS") == 0
    assert first.get_tag("NM") == 4
    assert first.get_tag("rh") == 1
    assert first.mapping_quality == 30

    assert second.reference_name == "chr3"
    assert second.reference_id == rec.header.get_tid("chr3")
    assert second.reference_start == 170653466
    assert second.is_forward
    assert second.query_sequence == rec.query_sequence
    assert second.query_qualities == rec.query_qualities
    assert second.cigarstring == "49M"
    assert second.get_tag("AS") == 0
    assert second.get_tag("NM") == 4
    assert second.get_tag("rh") == 1
    assert second.mapping_quality == 20

    for result in (first, second):
        assert result.query_name == rec.query_name
        assert result.is_read1 is rec.is_read1
        assert result.is_read2 is rec.is_read2
        assert result.is_duplicate is rec.is_duplicate
        assert result.is_paired is rec.is_paired
        assert not result.is_proper_pair
        assert result.is_qcfail is rec.is_qcfail
        assert result.is_secondary
        assert not result.is_supplementary
        assert result.is_mapped

        assert result.next_reference_id == mate.reference_id
        assert result.next_reference_name == mate.reference_name
        assert result.next_reference_start == mate.reference_start
        assert result.mate_is_mapped is mate.is_mapped
        assert result.mate_is_reverse is mate.is_reverse
        assert result.get_tag("MC") == mate.cigarstring
        assert result.get_tag("ms") == sum_of_base_qualities(mate)
        assert result.get_tag("MQ") == mate.mapping_quality
        assert result.get_tag("RG") == rec.get_tag("RG")
        assert result.get_tag("RX") == rec.get_tag("RX")


def test_many_sam_from_rec_with_hard_clips() -> None:
    """Test that we can't reconstruct the bases and qualities if there are hard clips."""
    value: str = "chr9,-104599381,31M,4,0,30"
    builder = SamBuilder()
    rec, _ = builder.add_pair(chrom="chr1", start1=32, start2=49, cigar1="1H30M")

    assert rec.query_sequence is not None  # for type narrowing
    assert rec.query_qualities is not None  # for type narrowing
    assert list(SecondaryAlignment.many_from_rec(rec)) == []

    rec.set_tag("XB", value)

    (actual,) = SecondaryAlignment.many_sam_from_rec(rec)

    assert actual.query_sequence == NO_QUERY_BASES


def test_add_to_template() -> None:
    """Test that we add secondary alignments as SAM records to a template."""
    value: str = "chr9,-104599381,49M,4,0,30;chr3,+170653467,49M,4,0,20;;;"  # with trailing ';'
    builder = SamBuilder()
    rec = builder.add_single(chrom="chr1", start=32)
    rec.set_tag("RX", "ACGT")

    assert list(SecondaryAlignment.many_from_rec(rec)) == []

    rec.set_tag("XB", value)

    actual = SecondaryAlignment.add_to_template(Template.build([rec]))
    expected = Template.build([rec] + list(SecondaryAlignment.many_sam_from_rec(rec)))

    assert actual == expected
