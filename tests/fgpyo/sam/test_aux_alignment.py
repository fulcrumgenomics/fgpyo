from typing import Any

import pytest

from fgpyo.sam import NO_QUERY_BASES
from fgpyo.sam import AuxAlignment
from fgpyo.sam import Cigar
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
                "mapping_quality": 30,
            },
            "Reference start cannot be less than 0! Found: -1",
        ),
        (
            {
                "reference_name": "chr9",
                "reference_start": 123232,
                "is_forward": False,
                "cigar": Cigar.from_cigarstring("49M"),
                "edit_distance": -1,
                "alignment_score": 0,
                "mapping_quality": 30,
            },
            "Edit distance cannot be less than 0! Found: -1",
        ),
        # TODO: figure out if we want this check.
        #       (
        #           {
        #               "reference_name": "chr9",
        #               "reference_start": 123232,
        #               "is_forward": False,
        #               "cigar": Cigar.from_cigarstring("49M"),
        #               "edit_distance": 4,
        #               "alignment_score": -1,
        #               "mapping_quality": 30,
        #           },
        #           "Alignment score cannot be less than 0! Found: -1",
        #       ),
        (
            {
                "reference_name": "chr9",
                "reference_start": 123232,
                "is_forward": False,
                "cigar": Cigar.from_cigarstring("49M"),
                "edit_distance": 4,
                "alignment_score": 4,
                "mapping_quality": -1,
            },
            "Mapping quality cannot be less than 0! Found: -1",
        ),
    ],
)
def test_auxiliary_alignment_validation(kwargs: dict[str, Any], error: str) -> None:
    """Test that we raise exceptions for invalid arguments to AuxAlignment."""
    with pytest.raises(ValueError, match=error):
        AuxAlignment(**kwargs)


@pytest.mark.parametrize(
    ["tag", "value", "expected"],
    [
        [
            # Test a well-formed negatively stranded SA
            "SA",
            "chr9,104599381,-,49M,60,4,,,",
            AuxAlignment(
                reference_name="chr9",
                reference_start=104599380,
                is_forward=False,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=None,
                mapping_quality=60,
                is_secondary=False,
                is_supplementary=True,
            ),
        ],
        [
            # Test a positive stranded SA and extra trailing commas
            "SA",
            "chr9,104599381,+,49M,20,4,,,,,",
            AuxAlignment(
                reference_name="chr9",
                reference_start=104599380,
                is_forward=True,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=None,
                mapping_quality=20,
                is_secondary=False,
                is_supplementary=True,
            ),
        ],
        [
            # Test a well-formed negatively stranded XB
            "XB",
            "chr9,-104599381,49M,4,0,30",
            AuxAlignment(
                reference_name="chr9",
                reference_start=104599380,
                is_forward=False,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=0,
                mapping_quality=30,
                is_secondary=True,
                is_supplementary=False,
            ),
        ],
        [
            # Test a positive stranded XB and extra trailing commas
            "XB",
            "chr3,+170653467,49M,4,0,20,,,,",
            AuxAlignment(
                reference_name="chr3",
                reference_start=170653466,
                is_forward=True,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=0,
                mapping_quality=20,
                is_secondary=True,
                is_supplementary=False,
            ),
        ],
        [
            # Test a well-formed negatively stranded XA
            "XA",
            "chr9,-104599381,49M,4",
            AuxAlignment(
                reference_name="chr9",
                reference_start=104599380,
                is_forward=False,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=None,
                mapping_quality=None,
                is_secondary=True,
                is_supplementary=False,
            ),
        ],
        [
            # Test a positive stranded XA and extra trailing commas
            "XA",
            "chr3,+170653467,49M,4,,,,",
            AuxAlignment(
                reference_name="chr3",
                reference_start=170653466,
                is_forward=True,
                cigar=Cigar.from_cigarstring("49M"),
                edit_distance=4,
                alignment_score=None,
                mapping_quality=None,
                is_secondary=True,
                is_supplementary=False,
            ),
        ],
    ],
)
def test_auxiliary_alignment_from_tag_value(tag: str, value: str, expected: AuxAlignment) -> None:
    """Test that we can build an SA, XA, or XB from a item of the tag value."""
    assert AuxAlignment.from_tag_value(tag, value) == expected


@pytest.mark.parametrize("tag", ["SA", "XA", "XB"])
def test_from_tag_value_invalid_number_of_commas(tag: str) -> None:
    """Test that we raise an exception if we don't have the right number of fields."""
    with pytest.raises(
        ValueError, match=rf"{tag} tag value has the incorrect number of fields: chr9,104599381"
    ):
        AuxAlignment.from_tag_value(tag, "chr9,104599381")


def test_from_tag_value_raises_invalid_multi_value() -> None:
    """Test that we raise an exception if we receive a multi-value."""
    with pytest.raises(
        ValueError,
        match=(
            r"Cannot parse a multi-value string! Found: "
            + r"chr3,\+170653467,49M,4;chr3,\+170653467,49M,4 for tag XA"
        ),
    ):
        AuxAlignment.from_tag_value("XA", "chr3,+170653467,49M,4;chr3,+170653467,49M,4")


def test_from_tag_value_raises_invalid_tag() -> None:
    """Test that we raise an exception if we receive an unsupported SAM tag."""
    with pytest.raises(ValueError, match="Tag XF is not one of SA, XA, XB!"):
        AuxAlignment.from_tag_value("XF", "chr3,+170653467,49M,4")


def test_from_tag_value_raises_for_invalid_sa_strand() -> None:
    """Test that we raise an exception when strand is malformed for an SA value."""
    with pytest.raises(ValueError, match=r"The strand field is not either '\+' or '-': !"):
        AuxAlignment.from_tag_value("SA", "chr3,2000,!,49M,60,4")


@pytest.mark.parametrize("stranded_start", ["!1", "1"])
def test_from_tag_value_raises_for_invalid_xa_stranded_start(stranded_start: str) -> None:
    """Test that we raise an exception when stranded start is malformed for an XA value."""
    with pytest.raises(
        ValueError, match=f"The stranded start field is malformed: {stranded_start}"
    ):
        AuxAlignment.from_tag_value("XA", f"chr3,{stranded_start},49M,4")


@pytest.mark.parametrize("stranded_start", ["!1", "1"])
def test_from_tag_value_raises_for_invalid_xb_stranded_start(stranded_start: str) -> None:
    """Test that we raise an exception when stranded start is malformed for an XA value."""
    with pytest.raises(
        ValueError, match=f"The stranded start field is malformed: {stranded_start}"
    ):
        AuxAlignment.from_tag_value("XB", f"chr3,{stranded_start},49M,4,0,20")


@pytest.mark.parametrize(
    ["auxiliary", "expected"],
    [
        (
            AuxAlignment(
                reference_name="chr3",
                reference_start=170653466,
                is_forward=True,
                cigar=Cigar.from_cigarstring("1H49M"),
                edit_distance=4,
            ),
            170653466 + 49,
        ),
        (
            AuxAlignment(
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
def test_auxiliary_alignment_reference_end_property(auxiliary: AuxAlignment, expected: int) -> None:
    """Test that we correctly calculate reference end based on start and cigar."""
    assert auxiliary.reference_end == expected


def test_many_from_rec() -> None:
    """Test that we can build many auxiliary alignments from multiple parts in a tag value."""
    builder = SamBuilder()
    rec = builder.add_single()
    rec.set_tag("XA", "chr9,-104599381,49M,4;chr3,+170653467,49M,4;;;")

    assert AuxAlignment.many_from_rec(rec) == [
        AuxAlignment(
            reference_name="chr9",
            reference_start=104599380,
            is_forward=False,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapping_quality=None,
            is_secondary=True,
            is_supplementary=False,
        ),
        AuxAlignment(
            reference_name="chr3",
            reference_start=170653466,
            is_forward=True,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapping_quality=None,
            is_secondary=True,
            is_supplementary=False,
        ),
    ]


def test_many_from_rec_returns_no_auxiliaries_when_unmapped() -> None:
    """Test that many_from_rec returns no auxiliary alignments when unmapped."""
    builder = SamBuilder()
    rec = builder.add_single()
    assert rec.is_unmapped
    assert len(list(AuxAlignment.many_from_rec(rec))) == 0


def test_sa_many_from_rec() -> None:
    """Test that we return supplementary alignments from a SAM record with multiple SAs."""
    value: str = "chr9,104599381,-,49M,20,4;chr3,170653467,+,49M,30,4;;;"  # with trailing ';'
    builder = SamBuilder()
    rec = builder.add_single(chrom="chr1", start=32)

    assert list(AuxAlignment.many_from_rec(rec)) == []

    rec.set_tag("SA", value)

    assert list(AuxAlignment.many_from_rec(rec)) == [
        AuxAlignment(
            reference_name="chr9",
            reference_start=104599380,
            is_forward=False,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapping_quality=20,
            is_secondary=False,
            is_supplementary=True,
        ),
        AuxAlignment(
            reference_name="chr3",
            reference_start=170653466,
            is_forward=True,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapping_quality=30,
            is_secondary=False,
            is_supplementary=True,
        ),
    ]


def test_xa_many_from_rec() -> None:
    """Test that we return secondary alignments from a SAM record with multiple XAs."""
    value: str = "chr9,-104599381,49M,4;chr3,+170653467,49M,4;;;"  # with trailing ';'
    builder = SamBuilder()
    rec = builder.add_single(chrom="chr1", start=32)

    assert list(AuxAlignment.many_from_rec(rec)) == []

    rec.set_tag("XA", value)

    assert list(AuxAlignment.many_from_rec(rec)) == [
        AuxAlignment(
            reference_name="chr9",
            reference_start=104599380,
            is_forward=False,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapping_quality=None,
            is_secondary=True,
            is_supplementary=False,
        ),
        AuxAlignment(
            reference_name="chr3",
            reference_start=170653466,
            is_forward=True,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=None,
            mapping_quality=None,
            is_secondary=True,
            is_supplementary=False,
        ),
    ]


def test_xb_many_from_rec() -> None:
    """Test that we return secondary alignments from a SAM record with multiple XBs."""
    value: str = "chr9,-104599381,49M,4,0,30;chr3,+170653467,49M,4,0,20;;;"  # with trailing ';'
    builder = SamBuilder()
    rec = builder.add_single(chrom="chr1", start=32)

    assert list(AuxAlignment.many_from_rec(rec)) == []

    rec.set_tag("XB", value)

    assert list(AuxAlignment.many_from_rec(rec)) == [
        AuxAlignment(
            reference_name="chr9",
            reference_start=104599380,
            is_forward=False,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=0,
            mapping_quality=30,
            is_secondary=True,
            is_supplementary=False,
        ),
        AuxAlignment(
            reference_name="chr3",
            reference_start=170653466,
            is_forward=True,
            cigar=Cigar.from_cigarstring("49M"),
            edit_distance=4,
            alignment_score=0,
            mapping_quality=20,
            is_secondary=True,
            is_supplementary=False,
        ),
    ]


def test_many_pysam_from_rec_returns_no_auxiliaries_when_unmapped() -> None:
    """Test that many_pysam_from_rec returns no auxiliaries when unmapped."""
    builder = SamBuilder()
    rec = builder.add_single()
    assert rec.is_unmapped
    assert len(list(AuxAlignment.many_pysam_from_rec(rec))) == 0


def test_sa_many_pysam_from_rec() -> None:
    """Test that we return supp. alignments as SAM records from a record with multiple SAs."""
    value: str = "chr9,104599381,-,49M,20,4;chr3,170653467,+,49M,20,4;;;"  # with trailing ';'
    builder = SamBuilder()
    rec, mate = builder.add_pair(chrom="chr1", start1=32, start2=49)
    rec.set_tag("RX", "ACGT")

    assert rec.query_sequence is not None  # for type narrowing
    assert rec.query_qualities is not None  # for type narrowing
    assert list(AuxAlignment.many_from_rec(rec)) == []

    rec.set_tag("SA", value)
    first, second = list(AuxAlignment.many_pysam_from_rec(rec))

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
    assert first.mapping_quality == 20

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
    assert second.mapping_quality == 20

    for result in (first, second):
        assert result.query_name == rec.query_name
        assert result.is_read1 is rec.is_read1
        assert result.is_read2 is rec.is_read2
        assert result.is_duplicate is rec.is_duplicate
        assert result.is_paired is rec.is_paired
        assert result.is_proper_pair
        assert result.is_qcfail is rec.is_qcfail
        assert not result.is_secondary
        assert result.is_supplementary
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


def test_xa_many_pysam_from_rec() -> None:
    """Test that we return secondary alignments as SAM records from a record with multiple XAs."""
    value: str = "chr9,-104599381,49M,4;chr3,+170653467,49M,4;;;"  # with trailing ';'
    builder = SamBuilder()
    rec, mate = builder.add_pair(chrom="chr1", start1=32, start2=49)
    rec.set_tag("RX", "ACGT")

    assert rec.query_sequence is not None  # for type narrowing
    assert rec.query_qualities is not None  # for type narrowing
    assert list(AuxAlignment.many_from_rec(rec)) == []

    rec.set_tag("XB", value)
    first, second = list(AuxAlignment.many_pysam_from_rec(rec))

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


def test_xb_many_pysam_from_rec() -> None:
    """Test that we return secondary alignments as SAM records from a record with multiple XBs."""
    value: str = "chr9,-104599381,49M,4,0,30;chr3,+170653467,49M,4,0,20;;;"  # with trailing ';'
    builder = SamBuilder()
    rec, mate = builder.add_pair(chrom="chr1", start1=32, start2=49)
    rec.set_tag("RX", "ACGT")

    assert rec.query_sequence is not None  # for type narrowing
    assert rec.query_qualities is not None  # for type narrowing
    assert list(AuxAlignment.many_from_rec(rec)) == []

    rec.set_tag("XB", value)
    first, second = list(AuxAlignment.many_pysam_from_rec(rec))

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


def test_many_pysam_from_rec_with_hard_clips() -> None:
    """Test that we can't reconstruct the bases and qualities if there are hard clips."""
    value: str = "chr9,-104599381,31M,4,0,30"
    builder = SamBuilder()
    rec, _ = builder.add_pair(chrom="chr1", start1=32, start2=49, cigar1="1H30M")

    assert rec.query_sequence is not None  # for type narrowing
    assert rec.query_qualities is not None  # for type narrowing
    assert list(AuxAlignment.many_pysam_from_rec(rec)) == []

    rec.set_tag("XB", value)

    (actual,) = AuxAlignment.many_pysam_from_rec(rec)

    assert actual.query_sequence == NO_QUERY_BASES
