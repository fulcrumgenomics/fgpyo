import pytest

from fgpyo.vcf.builder import VariantBuilder
from fgpyo.vcf.variant_ordering import VariantOrdering
from pysam import VariantHeader

@pytest.mark.parametrize(
    "rec1_contig,rec1_pos,rec2_contig,rec2_pos,expected",
    [
        ("chr1", 100, "chr1", 100, True),
        ("chr1", 100, "chr1", 101, False),
        ("chr1", 100, "chr2", 100, False),
    ],
)
def test_variant_ordering_eq(
    rec1_contig: str, rec1_pos: int, rec2_contig: str, rec2_pos: int, expected: bool
) -> None:
    """Test the equality comparison of VariantOrdering."""
    builder: VariantBuilder = VariantBuilder()
    rec1 = builder.add(contig=rec1_contig, pos=rec1_pos)
    rec2 = builder.add(contig=rec2_contig, pos=rec2_pos)

    vo = VariantOrdering(header=builder.header)

    assert vo.eq(rec1, rec2) is expected


@pytest.mark.parametrize(
    "rec1_contig,rec1_pos,rec2_contig,rec2_pos,expected",
    [
        ("chr1", 100, "chr1", 100, False),
        ("chr1", 100, "chr1", 101, True),
        ("chr1", 101, "chr1", 100, False),
        ("chr1", 100, "chr2", 100, True),
        ("chr2", 100, "chr1", 100, False),
    ],
)
def test_variant_ordering_lt(
    rec1_contig: str, rec1_pos: int, rec2_contig: str, rec2_pos: int, expected: bool
) -> None:
    """Test the less than comparison of VariantOrdering."""
    builder: VariantBuilder = VariantBuilder()
    rec1 = builder.add(contig=rec1_contig, pos=rec1_pos)
    rec2 = builder.add(contig=rec2_contig, pos=rec2_pos)

    vo = VariantOrdering(header=builder.header)

    assert vo.lt(rec1, rec2) is expected


@pytest.mark.parametrize(
    "rec1_contig,rec1_pos,rec2_contig,rec2_pos,expected",
    [
        ("chr1", 100, "chr1", 100, False),
        ("chr1", 100, "chr1", 101, False),
        ("chr1", 101, "chr1", 100, True),
        ("chr1", 100, "chr2", 100, False),
        ("chr2", 100, "chr1", 100, True),
    ],
)
def test_variant_ordering_gt(
    rec1_contig: str, rec1_pos: int, rec2_contig: str, rec2_pos: int, expected: bool
) -> None:
    """Test the greater than comparison of VariantOrdering."""
    builder: VariantBuilder = VariantBuilder()
    rec1 = builder.add(contig=rec1_contig, pos=rec1_pos)
    rec2 = builder.add(contig=rec2_contig, pos=rec2_pos)

    vo = VariantOrdering(header=builder.header)

    assert vo.gt(rec1, rec2) is expected


@pytest.mark.parametrize(
    "rec1_contig,rec1_pos,rec2_contig,rec2_pos,expected",
    [
        ("chr1", 100, "chr1", 100, 0),
        ("chr1", 100, "chr1", 101, -1),
        ("chr1", 101, "chr1", 100, 1),
        ("chr1", 100, "chr2", 100, -1),
        ("chr2", 100, "chr1", 100, 1),
    ],
)
def test_variant_ordering_cmp(
    rec1_contig: str, rec1_pos: int, rec2_contig: str, rec2_pos: int, expected: int
) -> None:
    """Test the comparison done by VariantOrdering."""
    builder: VariantBuilder = VariantBuilder()
    rec1 = builder.add(contig=rec1_contig, pos=rec1_pos)
    rec2 = builder.add(contig=rec2_contig, pos=rec2_pos)

    vo = VariantOrdering(header=builder.header)

    assert vo.cmp(rec1, rec2) == expected


def test_variant_ordering_sort_variants() -> None:
    """Test VariantOrdering sort_variants."""
    builder: VariantBuilder = VariantBuilder()
    rec1 = builder.add(contig="chr1", pos=200)
    rec2 = builder.add(contig="chr1", pos=100)
    rec3 = builder.add(contig="chr2", pos=150)
    rec4 = builder.add(contig="chr2", pos=50)

    vo = VariantOrdering(header=builder.header)

    sorted_recs = vo.sort_variants([rec1, rec2, rec3, rec4])
    expected_order = [rec2, rec1, rec4, rec3]

    assert sorted_recs == expected_order


def test_variant_ordering_invalid_contig() -> None:
    """Test that VariantOrdering raises an error for invalid contigs."""
    builder: VariantBuilder = VariantBuilder()
    rec1 = builder.add(contig="chr1", pos=100)

    ordering_header = VariantHeader() # Empty header with no contigs
    vo = VariantOrdering(header=ordering_header)

    with pytest.raises(ValueError, match="Contig 'chr1' not found in VCF header."):
        vo.validate_contig(rec1)
