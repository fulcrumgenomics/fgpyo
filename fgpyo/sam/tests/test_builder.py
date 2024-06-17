"""Basic tests of the builder module."""

from pathlib import Path
from typing import List
from typing import Optional

import pytest

from fgpyo import sam
from fgpyo.sam import SamOrder
from fgpyo.sam.builder import SamBuilder


def test_add_pair_all_fields() -> None:
    builder = SamBuilder()
    builder.add_pair(
        name="q1",
        chrom="chr1",
        bases1="ACGTG",
        quals1=[20, 21, 22, 23, 24],
        start1=10000,
        cigar1="5M",
        mapq1=51,
        strand1="+",
        bases2="GCGC",
        quals2=[30, 31, 32, 33],
        start2=10200,
        cigar2="4M",
        mapq2=52,
        strand2="-",
        attrs={"aa": "Hello", "bb": 42},
    )
    recs = builder.to_sorted_list()
    assert len(recs) == 2
    for rec in recs:
        assert rec.query_name == "q1"
        assert rec.reference_name == "chr1"
        assert rec.is_paired
        assert abs(rec.template_length) == 204
        assert rec.get_tag("aa") == "Hello"
        assert rec.get_tag("bb") == 42
        if rec.is_read1:
            assert rec.reference_start == 10000
            assert not rec.is_reverse
            assert rec.query_sequence == "ACGTG"
            assert list(rec.query_qualities) == [20, 21, 22, 23, 24]
            assert rec.cigarstring == "5M"
            assert rec.mapping_quality == 51
        else:
            assert rec.reference_start == 10200
            assert rec.is_reverse
            assert rec.query_sequence == "GCGC"
            assert list(rec.query_qualities) == [30, 31, 32, 33]
            assert rec.cigarstring == "4M"
            assert rec.mapping_quality == 52


def test_add_pair_minimal() -> None:
    builder = SamBuilder(r1_len=10, r2_len=5, base_quality=25, mapping_quality=20)
    r1, r2 = builder.add_pair(chrom="chr1", start1=1000, start2=1200)
    assert r1.query_name == r2.query_name
    assert r1.reference_name == r2.reference_name == "chr1"
    assert r1.reference_start == 1000
    assert r2.reference_start == 1200
    assert not r1.is_reverse
    assert r2.is_reverse
    assert len(r1.query_sequence) == len(r1.query_qualities) == 10
    assert len(r2.query_sequence) == len(r2.query_qualities) == 5
    assert r1.cigarstring == "10M"
    assert r2.cigarstring == "5M"
    assert r1.mapping_quality == 20
    assert r2.mapping_quality == 20
    assert r1.get_tag("RG") == builder.rg_id()
    assert r2.get_tag("RG") == builder.rg_id()


def test_add_pair_mix_and_match() -> None:
    builder = SamBuilder(r1_len=100, r2_len=100, base_quality=30)
    r1, r2 = builder.add_pair(chrom="chr1", start1=500, start2=700, cigar1="75M", cigar2="9M1I30M")
    assert len(r1.query_sequence) == len(r1.query_qualities) == 75
    assert len(r2.query_sequence) == len(r2.query_qualities) == 40

    r1, r2 = builder.add_pair(
        chrom="chr1", start1=500, start2=700, bases1="ACGTGCATGC", bases2="ACGAC"
    )
    assert len(r1.query_sequence) == len(r1.query_qualities) == 10
    assert len(r2.query_sequence) == len(r2.query_qualities) == 5
    assert r1.cigarstring == "10M"
    assert r2.cigarstring == "5M"

    r1, r2 = builder.add_pair(
        chrom="chr1", start1=500, start2=700, quals1=[30] * 20, quals2=[20] * 10
    )
    assert len(r1.query_sequence) == len(r1.query_qualities) == 20
    assert len(r2.query_sequence) == len(r2.query_qualities) == 10
    assert r1.cigarstring == "20M"
    assert r2.cigarstring == "10M"

    # Now what if we provide multiple values that are inconsistent
    with pytest.raises(ValueError, match="not length compatible"):
        builder.add_pair(chrom="chr1", start1=10, start2=99, bases1="ACGTG", cigar1="10M")

    with pytest.raises(ValueError, match="not length compatible"):
        builder.add_pair(chrom="chr1", start1=10, start2=99, bases1="ACGTG", quals1=[2, 2])

    with pytest.raises(ValueError, match="not length compatible"):
        builder.add_pair(chrom="chr1", start1=10, start2=99, quals1=[2, 2], cigar1="5M")


def test_unmapped_reads() -> None:
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=1000)
    assert not r1.is_unmapped
    assert r1.mate_is_unmapped
    assert r2.is_unmapped
    assert not r2.mate_is_unmapped
    for rec in r1, r2:
        assert rec.reference_name == "chr1"
        assert rec.reference_start == 1000
        assert rec.next_reference_name == "chr1"
        assert rec.next_reference_start == 1000

    r1, r2 = builder.add_pair(chrom="chr1", start2=2000)
    assert r1.is_unmapped
    assert not r1.mate_is_unmapped
    assert not r2.is_unmapped
    assert r2.mate_is_unmapped
    for rec in r1, r2:
        assert rec.reference_name == "chr1"
        assert rec.reference_start == 2000
        assert rec.next_reference_name == "chr1"
        assert rec.next_reference_start == 2000

    r1, r2 = builder.add_pair(chrom=sam.NO_REF_NAME)
    assert r1.is_unmapped
    assert r1.mate_is_unmapped
    assert r2.is_unmapped
    assert r2.mate_is_unmapped
    for rec in r1, r2:
        assert rec.reference_name is None
        assert rec.reference_start == sam.NO_REF_POS
        assert rec.next_reference_name is None
        assert rec.next_reference_start == sam.NO_REF_POS


def test_invalid_strand() -> None:
    with pytest.raises(ValueError, match="strand"):
        SamBuilder().add_pair(chrom="chr1", start1=100, start2=200, strand1="F", strand2="R")


def test_proper_pair() -> None:
    builder = SamBuilder()

    # Regular innies
    for rec in builder.add_pair(chrom="chr1", start1=5000, start2=5200, strand1="+", strand2="-"):
        assert rec.is_proper_pair
    for rec in builder.add_pair(chrom="chr1", start1=5200, start2=5000, strand1="-", strand2="+"):
        assert rec.is_proper_pair

    # Outies
    for rec in builder.add_pair(chrom="chr1", start1=5000, start2=5200, strand1="-", strand2="+"):
        assert not rec.is_proper_pair
    for rec in builder.add_pair(chrom="chr1", start1=5200, start2=5000, strand1="+", strand2="-"):
        assert not rec.is_proper_pair

    # Unmapped
    for rec in builder.add_pair(chrom="chr1", start1=5000, strand1="+"):
        assert not rec.is_proper_pair
    for rec in builder.add_pair(chrom="chr1", start2=5000, strand2="+"):
        assert not rec.is_proper_pair
    for rec in builder.add_pair():
        assert not rec.is_proper_pair


def test_chrom1_chrom2() -> None:
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom1="chr1", start1=1000, chrom2="chr2", start2=1000)

    assert r1.query_name == r2.query_name
    assert r1.reference_name == "chr1"
    assert r2.reference_name == "chr2"
    assert r1.reference_start == 1000
    assert r2.reference_start == 1000
    assert not r1.is_reverse
    assert r2.is_reverse

    r1, r2 = builder.add_pair(chrom1="chr1", start1=1000)
    assert not r1.is_unmapped
    assert r2.is_unmapped

    r1, r2 = builder.add_pair(chrom2="chr1", start2=1000)
    assert not r2.is_unmapped
    assert r1.is_unmapped

    with pytest.raises(ValueError, match="start2 cannot be used on its own"):
        r1, r2 = builder.add_pair(chrom1="chr1", start1=1000, start2=1000)

    with pytest.raises(ValueError, match="start1 cannot be used on its own"):
        r1, r2 = builder.add_pair(chrom2="chr1", start1=1000, start2=1000)

    with pytest.raises(ValueError, match="Cannot use chrom in combination with"):
        r1, r2 = builder.add_pair(chrom="chr1", chrom1="chr1", start1=1000, start2=1000)

    with pytest.raises(ValueError, match="Cannot use chrom in combination with"):
        r1, r2 = builder.add_pair(chrom="chr1", chrom2="chr1", start1=1000, start2=1000)


def test_add_single() -> None:
    builder = SamBuilder(r1_len=25, r2_len=50)

    # Unmapped fragment
    r = builder.add_single()
    assert not r.is_paired
    assert r.is_unmapped
    assert len(r.query_sequence) == 25

    # Supplementary R1
    r = builder.add_single(name="q1", read_num=1, chrom="chr1", start=1000, supplementary=True)
    assert r.is_paired
    assert r.is_read1
    assert not r.is_read2
    assert not r.is_unmapped
    assert r.is_supplementary
    assert len(r.query_sequence) == 25

    # A read two
    r = builder.add_single(name="q1", read_num=2, chrom="chr1", start=1000)
    assert r.is_paired
    assert not r.is_read1
    assert r.is_read2
    assert not r.is_unmapped
    assert len(r.query_sequence) == 50

    with pytest.raises(ValueError, match="read_num"):
        builder.add_single(read_num=0)


def test_sorting() -> None:
    builder = SamBuilder()
    builder.add_pair(chrom="chr1", start1=5000, start2=4700, strand1="-", strand2="+")
    builder.add_pair(chrom="chr1", start1=4000, start2=4300)
    builder.add_pair(chrom="chr5", start1=4000, start2=4300)
    builder.add_pair(chrom="chr2", start1=4000, start2=4300)

    last_ref_id = -1
    last_start = -1
    for rec in builder.to_sorted_list():
        ref_id = rec.reference_id
        start = rec.reference_start
        assert ref_id > last_ref_id or (ref_id == last_ref_id and start >= last_start)
        last_ref_id = ref_id
        last_start = start


def make_sort_order_builder(tmp_path: Path, sort_order: SamOrder) -> Path:
    builder = SamBuilder(sort_order=sort_order)
    builder.add_pair(name="test3", chrom="chr1", start1=5000, start2=4700, strand1="-", strand2="+")
    builder.add_pair(name="test2", chrom="chr1", start1=4000, start2=4300)
    builder.add_pair(name="test1", chrom="chr5", start1=4000, start2=4300)
    builder.add_pair(name="test4", chrom="chr2", start1=4000, start2=4300)

    pos_path = tmp_path / "test.bam"
    builder.to_path(pos_path)
    return pos_path


@pytest.mark.parametrize(
    argnames=["sort_order", "expected_name_order"],
    argvalues=[
        (SamOrder.Coordinate, ["test2", "test3", "test4", "test1"]),
        (SamOrder.QueryName, ["test1", "test2", "test3", "test4"]),
        (SamOrder.Unsorted, ["test3", "test2", "test1", "test4"]),
        (SamOrder.Unknown, ["test3", "test2", "test1", "test4"]),
    ],
    ids=["Coordinate sorting", "Query name sorting", "Unsorted output", "Unknown sorting"],
)
def test_sort_types(
    tmp_path: Path, sort_order: Optional[SamOrder], expected_name_order: List[str]
) -> None:
    bam_path = make_sort_order_builder(tmp_path=tmp_path, sort_order=sort_order)
    with sam.reader(bam_path) as in_bam:
        for name in expected_name_order:
            read1 = next(in_bam)
            assert (
                name == read1.query_name
            ), "Position based read sort order did not match expectation"
            read2 = next(in_bam)
            assert (
                name == read2.query_name
            ), "Position based read sort order did not match expectation"


def test_custom_sd() -> None:
    builder1 = SamBuilder()
    builder2 = SamBuilder(sd=[{"SN": "hi", "LN": 999}, {"SN": "bye", "LN": 888}])
    builder1.add_pair(chrom="chr1", start1=200, start2=400)
    builder2.add_pair(chrom="hi", start1=200, start2=400)

    with pytest.raises(ValueError, match="not a valid chromosome name"):
        builder1.add_pair(chrom="hi", start1=200, start2=400)

    with pytest.raises(ValueError, match="not a valid chromosome name"):
        builder2.add_pair(chrom="chr1", start1=200, start2=400)


def test_custom_rg() -> None:
    builder = SamBuilder(rg={"ID": "novel", "SM": "custom_rg", "LB": "foo", "PL": "ILLUMINA"})
    for rec in builder.add_pair(chrom="chr1", start1=100, start2=200):
        assert rec.get_tag("RG") == "novel"
