"""Tests for :py:mod:`~fgpyo.clipping`"""

from typing import Optional

import pytest
from pysam import AlignedSegment

from fgpyo import sam
from fgpyo.sam import clipping
from fgpyo.sam.builder import SamBuilder


def r(start: Optional[int], cigar: Optional[str], strand: Optional[str] = "+") -> AlignedSegment:
    """ "Constructs a read for testing."""
    builder = SamBuilder()
    if start:
        r1, r2 = builder.add_pair(chrom="chr1", start1=start, cigar1=cigar, strand1=strand)
    else:
        r1, r2 = builder.add_pair()
    return r1


def test_make_read_unmapped() -> None:
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, start2=250)

    clipping._make_read_unmapped(r1)
    assert r1.is_unmapped
    assert r1.reference_id == sam.NO_REF_INDEX
    assert r1.reference_name is None
    assert r1.reference_start == sam.NO_REF_POS


###############################################################################
# Tests for read_pos_at_ref_pos()
###############################################################################


def test_read_pos_at_ref_pos_simple() -> None:
    rec = r(100, "100M")
    assert clipping._read_pos_at_ref_pos(rec, 100) == 0
    assert clipping._read_pos_at_ref_pos(rec, 150) == 50


def test_read_pos_at_ref_pos_fails_with_position_outside_range() -> None:
    rec = r(100, "100M")
    assert clipping._read_pos_at_ref_pos(rec, 100) == 0
    assert clipping._read_pos_at_ref_pos(rec, 199) == 99

    with pytest.raises(ValueError):
        clipping._read_pos_at_ref_pos(rec, 99)
    with pytest.raises(ValueError):
        clipping._read_pos_at_ref_pos(rec, 200)


def test_read_pos_at_ref_pos_with_indels_nearby() -> None:
    rec = r(100, "25M1D25M1I25M")
    assert clipping._read_pos_at_ref_pos(rec, 100) == 0
    assert clipping._read_pos_at_ref_pos(rec, 110) == 10
    assert clipping._read_pos_at_ref_pos(rec, 120) == 20
    assert clipping._read_pos_at_ref_pos(rec, 130) == 29
    assert clipping._read_pos_at_ref_pos(rec, 140) == 39
    assert clipping._read_pos_at_ref_pos(rec, 150) == 49
    assert clipping._read_pos_at_ref_pos(rec, 160) == 60


def test_read_pos_at_ref_pos_with_clipping() -> None:
    rec = r(100, "10S90M")
    assert clipping._read_pos_at_ref_pos(rec, 100) == 10


def test_read_pos_at_ref_pos_with_refpos_in_deletion() -> None:
    rec = r(100, "50M5D50M")
    assert clipping._read_pos_at_ref_pos(rec, 152) is None
    assert clipping._read_pos_at_ref_pos(rec, 152, previous=None) is None
    assert clipping._read_pos_at_ref_pos(rec, 152, previous=True) == 49
    assert clipping._read_pos_at_ref_pos(rec, 152, previous=False) == 50


###############################################################################
# Tests for softclip_start_of_alignment()
###############################################################################


def test_softclip_start_of_alignment_by_query_clips_10_aligned_bases() -> None:
    rec = r(10, "50M", "+")
    info = clipping.softclip_start_of_alignment_by_query(rec, 10)
    assert info.query_bases_clipped == 10
    assert info.ref_bases_clipped == 10
    assert rec.reference_start == 20
    assert rec.cigarstring == "10S40M"


def test_softclip_start_of_alignment_by_query_masking_qualities() -> None:
    for new_qual in None, 0, 2:
        rec = r(10, "50M", "+")
        clipping.softclip_start_of_alignment_by_query(rec, 10, clipped_base_quality=new_qual)
        quals = rec.query_qualities

        for i in range(0, 10):
            assert quals[i] == (30 if new_qual is None else new_qual)


def test_soft_clip_start_of_alignment_by_query_clips_10_aligned_and_inserted_bases() -> None:
    for strand in "+", "-":
        rec = r(10, "4M2I44M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 8
        assert rec.reference_start == 18
        assert rec.cigarstring == "10S40M"


def test_softclip_start_of_alignment_by_query_clips_10_aligned_and_deleted_bases() -> None:
    for strand in "+", "-":
        rec = r(10, "6M2D44M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 12
        assert rec.reference_start == 22
        assert rec.cigarstring == "10S40M"


def test_softclip_start_of_alignment_by_query_clips_10_more_bases() -> None:
    for strand in "+", "-":
        rec = r(10, "10S40M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 20
        assert rec.cigarstring == "20S30M"


def test_softclip_start_of_alignment_by_query_preserves_hard_clipping() -> None:
    for strand in "+", "-":
        rec = r(10, "10H40M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 20
        assert rec.cigarstring == "10H10S30M"


def test_softclip_start_of_alignment_by_query_with_complicated_cigar() -> None:
    for strand in "+", "-":
        rec = r(10, "2H4S16M10I5M5I10M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 20
        assert rec.cigarstring == "2H14S6M10I5M5I10M"


def test_softclip_start_of_alignment_by_query_consumes_rest_of_insertion() -> None:
    for strand in "+", "-":
        rec = r(10, "8M4I38M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 12
        assert info.ref_bases_clipped == 8
        assert rec.reference_start == 18
        assert rec.cigarstring == "12S38M"


def test_softclip_start_of_alignment_by_query_preserves_insertion_adjacent_to_clipping() -> None:
    for strand in "+", "-":
        rec = r(10, "10M4I36M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 20
        assert rec.cigarstring == "10S4I36M"


def test_softclip_start_of_alignment_by_query_removes_deletion_following_clipping() -> None:
    for strand in "+", "-":
        rec = r(10, "10M4D40M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 14
        assert rec.reference_start == 24
        assert rec.cigarstring == "10S40M"


def test_softclip_start_of_alignment_by_query_preserves_deletions_post_clipping_region() -> None:
    for strand in "+", "-":
        rec = r(10, "25M4D25M", strand)
        info = clipping.softclip_start_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 20
        assert rec.cigarstring == "10S15M4D25M"


def test_softclip_start_of_alignment_by_query_unmapped_reads_ok() -> None:
    rec = r(start=None, cigar=None)
    info = clipping.softclip_start_of_alignment_by_query(rec, 10)
    assert info.query_bases_clipped == 0
    assert info.ref_bases_clipped == 0


def test_softclip_start_of_alignment_by_query_unmaps_read_when_clipping_all_bases() -> None:
    rec = r(10, "50M")
    assert not rec.is_unmapped
    info = clipping.softclip_start_of_alignment_by_query(rec, 50)
    assert info.query_bases_clipped == 50
    assert info.ref_bases_clipped == 50
    assert rec.is_unmapped


###############################################################################
# Tests for softclip_end_of_alignment()
###############################################################################


def test_softclip_end_of_alignment_by_query_clips_last10_bases_of_fully_aligned_read() -> None:
    for strand in "+", "-":
        rec = r(10, "50M", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 10
        assert rec.cigarstring == "40M10S"


def test_softclip_end_of_alignment_by_query_masks_qualities_when_softclipping() -> None:
    for new_qual in None, 2:
        rec = r(10, "50M", "+")
        clipping.softclip_end_of_alignment_by_query(rec, 10, clipped_base_quality=new_qual)
        quals = rec.query_qualities

        for i in range(40, 50):
            assert quals[i] == (30 if new_qual is None else new_qual)


def test_soft_clip_end_of_alignment_by_query_clips_10_aligned_and_inserted_bases() -> None:
    for strand in "+", "-":
        rec = r(10, "44M2I4M", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 8
        assert rec.reference_start == 10
        assert rec.cigarstring == "40M10S"


def test_softclip_end_of_alignment_by_query_clips_10_aligned_and_deleted_bases() -> None:
    for strand in "+", "-":
        rec = r(10, "44M2D6M", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 12
        assert rec.reference_start == 10
        assert rec.cigarstring == "40M10S"


def test_softclip_end_of_alignment_by_query_clips_10_more_bases() -> None:
    for strand in "+", "-":
        rec = r(10, "40M10S", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 10
        assert rec.cigarstring == "30M20S"


def test_softclip_end_of_alignment_by_query_preserves_hard_clipping() -> None:
    for strand in "+", "-":
        rec = r(10, "40M10H", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 10
        assert rec.cigarstring == "30M10S10H"


def test_softclip_end_of_alignment_by_query_with_complicated_cigar() -> None:
    for strand in "+", "-":
        rec = r(10, "10M5I5M10I16M4S2H", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 10
        assert rec.cigarstring == "10M5I5M10I6M14S2H"


def test_softclip_end_of_alignment_by_query_consumes_rest_of_insertion() -> None:
    for strand in "+", "-":
        rec = r(10, "38M4I8M", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 12
        assert info.ref_bases_clipped == 8
        assert rec.reference_start == 10
        assert rec.cigarstring == "38M12S"


def test_softclip_end_of_alignment_by_query_preserves_insertion_following_clipping() -> None:
    for strand in "+", "-":
        rec = r(10, "36M4I10M", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 10
        assert rec.cigarstring == "36M4I10S"


def test_softclip_end_of_alignment_by_query_removes_deletion_following_clipping() -> None:
    for strand in "+", "-":
        rec = r(10, "40M4D10M", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 14
        assert rec.reference_start == 10
        assert rec.cigarstring == "40M10S"


def test_softclip_end_of_alignment_by_query_preserves_deletions_post_clipping_region() -> None:
    for strand in "+", "-":
        rec = r(10, "25M4D25M", strand)
        info = clipping.softclip_end_of_alignment_by_query(rec, 10)
        assert info.query_bases_clipped == 10
        assert info.ref_bases_clipped == 10
        assert rec.reference_start == 10
        assert rec.cigarstring == "25M4D15M10S"


def test_softclip_end_of_alignment_by_query_unmapped_reads_ok() -> None:
    rec = r(start=None, cigar=None)
    info = clipping.softclip_end_of_alignment_by_query(rec, 10)
    assert info.query_bases_clipped == 0
    assert info.ref_bases_clipped == 0


def test_softclip_end_of_alignment_by_query_makes_read_unmapped_when_clipping_all_bases() -> None:
    rec = r(10, "50M")
    assert not rec.is_unmapped
    info = clipping.softclip_end_of_alignment_by_query(rec, 50)
    assert info.query_bases_clipped == 50
    assert info.ref_bases_clipped == 50
    assert rec.is_unmapped


###############################################################################
# Tests for functions that clip _reference_ bases instead of query bases
###############################################################################


def test_softclip_start_of_alignment_by_ref_simple() -> None:
    rec = r(10, "50M")
    info = clipping.softclip_start_of_alignment_by_ref(rec, 10)
    assert info.query_bases_clipped == 10
    assert info.ref_bases_clipped == 10
    assert rec.reference_start == 20
    assert rec.cigarstring == "10S40M"


def test_softclip_start_of_alignment_by_ref_with_deletion() -> None:
    rec = r(10, "5M5D45M")
    info = clipping.softclip_start_of_alignment_by_ref(rec, 10)
    assert info.query_bases_clipped == 5
    assert info.ref_bases_clipped == 10
    assert rec.reference_start == 20
    assert rec.cigarstring == "5S45M"


def test_softclip_start_of_alignment_by_ref_with_insertion() -> None:
    rec = r(10, "5M5I45M")
    info = clipping.softclip_start_of_alignment_by_ref(rec, 10)
    assert info.query_bases_clipped == 15
    assert info.ref_bases_clipped == 10
    assert rec.reference_start == 20
    assert rec.cigarstring == "15S40M"


def test_softclip_end_of_alignment_by_ref_simple() -> None:
    rec = r(10, "50M")
    info = clipping.softclip_end_of_alignment_by_ref(rec, 10)
    assert info.query_bases_clipped == 10
    assert info.ref_bases_clipped == 10
    assert rec.reference_start == 10
    assert rec.cigarstring == "40M10S"


def test_softclip_end_of_alignment_by_ref_with_deletion() -> None:
    rec = r(10, "45M5D5M")
    info = clipping.softclip_end_of_alignment_by_ref(rec, 10)
    assert info.query_bases_clipped == 5
    assert info.ref_bases_clipped == 10
    assert rec.reference_start == 10
    assert rec.cigarstring == "45M5S"


def test_softclip_end_of_alignment_by_ref_with_insertion() -> None:
    rec = r(10, "45M5I5M")
    info = clipping.softclip_end_of_alignment_by_ref(rec, 10)
    assert info.query_bases_clipped == 15
    assert info.ref_bases_clipped == 10
    assert rec.reference_start == 10
    assert rec.cigarstring == "40M15S"
