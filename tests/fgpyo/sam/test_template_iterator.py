from pathlib import Path

import pytest

from fgpyo.sam import AuxAlignment
from fgpyo.sam import Template
from fgpyo.sam import TemplateIterator
from fgpyo.sam import reader
from fgpyo.sam import writer
from fgpyo.sam.builder import SamBuilder


def test_template_init_function() -> None:
    builder: SamBuilder = SamBuilder()
    builder.add_pair(name="x", chrom="chr1", start1=1, start2=2)
    r1 = builder.to_sorted_list()[0]
    r2 = builder.to_sorted_list()[1]
    template = Template(
        name="foo",
        r1=r1,
        r2=r2,
        r1_supplementals=[r1],
        r2_supplementals=[r1, r2],
        r1_secondaries=[],
        r2_secondaries=[r2],
    )
    assert template.r1.query_name == "x"
    assert template.r2.reference_start == 2
    assert len([t for t in template.r1_supplementals]) == 1
    assert len([t for t in template.r1_secondaries]) == 0


def test_all_r1_and_all_r2() -> None:
    builder: SamBuilder = SamBuilder()
    (r1, r2) = builder.add_pair(name="x", chrom="chr1", start1=1, start2=2)
    (r1_secondary, r2_secondary) = builder.add_pair(name="x", chrom="chr1", start1=10, start2=12)
    r1_secondary.is_secondary = True
    r2_secondary.is_secondary = True
    (r1_supplementary, r2_supplementary) = builder.add_pair(
        name="x", chrom="chr1", start1=4, start2=6
    )
    r1_supplementary.is_supplementary = True
    r2_supplementary.is_supplementary = True

    template = Template.build(builder.to_unsorted_list())
    expected = Template(
        name="x",
        r1=r1,
        r2=r2,
        r1_secondaries=[r1_secondary],
        r2_secondaries=[r2_secondary],
        r1_supplementals=[r1_supplementary],
        r2_supplementals=[r2_supplementary],
    )

    assert template == expected
    assert list(template.all_r1s()) == [r1, r1_secondary, r1_supplementary]
    assert list(template.all_r2s()) == [r2, r2_secondary, r2_supplementary]


def test_to_templates() -> None:
    builder = SamBuilder()

    # Series of alignments for one template
    builder.add_pair(name="q1", chrom="chr1", start1=1, start2=2)
    builder.add_single(name="q1", read_num=1, chrom="chr1", start=1, supplementary=True)
    builder.add_single(name="q1", read_num=1, chrom="chr1", start=11, supplementary=True)
    builder.add_single(name="q1", read_num=2, chrom="chr1", start=2, supplementary=True)
    builder.add_single(name="q1", read_num=1, chrom="chr1", start=1, secondary=True)
    builder.add_single(name="q1", read_num=2, chrom="chr1", start=2, secondary=True)

    # Another template that has only R1s
    builder.add_single(name="q2", read_num=None, chrom="chr1", start=2)
    builder.add_single(name="q2", read_num=None, chrom="chr2", start=2, secondary=True)

    # Build templates
    iterator = iter(builder.to_unsorted_list())
    templates = list(Template.iterator(iterator))
    assert len(templates) == 2
    template1, template2 = templates

    # Check template 1
    assert template1.name == "q1"
    assert template1.r1.query_name == "q1"
    assert template1.r2.query_name == "q1"
    assert len(template1.r1_supplementals) == 2
    assert len(template1.r2_supplementals) == 1
    assert len(template1.r1_secondaries) == 1
    assert len(template1.r2_secondaries) == 1
    assert len(list(template1.primary_recs())) == 2
    assert len(list(template1.all_recs())) == 7

    # Check template 2
    assert template2.name == "q2"
    assert template2.r1.query_name == "q2"
    assert template2.r2 is None
    assert len(template2.r1_supplementals) == 0
    assert len(template2.r2_supplementals) == 0
    assert len(template2.r1_secondaries) == 1
    assert len(template2.r2_secondaries) == 0
    assert len(list(template2.primary_recs())) == 1
    assert len(list(template2.all_recs())) == 2


def test_write_template(
    tmp_path: Path,
) -> None:
    builder = SamBuilder()
    template = Template.build(
        [
            *builder.add_pair(name="r1", chrom="chr1", start1=100, start2=200),
            builder.add_single(name="r1", chrom="chr1", start=350, supplementary=True),
        ]
    )

    bam_path = tmp_path / "test.bam"

    # Test writing of all records
    with writer(bam_path, header=builder._samheader) as bam_writer:
        template.write_to(bam_writer)

    with reader(bam_path) as bam_reader:
        template = next(TemplateIterator(bam_reader))
        assert len([r for r in template.all_recs()]) == 3

    # Test primary-only
    with writer(bam_path, header=builder._samheader) as bam_writer:
        template.write_to(bam_writer, primary_only=True)

    with reader(bam_path) as bam_reader:
        template = next(TemplateIterator(bam_reader))
        assert len([r for r in template.all_recs()]) == 2


def test_template_can_set_r1_and_r2_with_no_secondary_or_supplementals() -> None:
    """Test that we can build a template with just an R1 and R2 primary alignment."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(name="x", chrom="chr1", start1=10, start2=30)
    actual = Template.build([r1, r2])
    expected = Template(
        name="x",
        r1=r1,
        r2=r2,
        r1_secondaries=[],
        r2_secondaries=[],
        r1_supplementals=[],
        r2_supplementals=[],
    )
    assert actual == expected


def test_template_treats_secondary_supplementary_as_supplementary() -> None:
    """Test that Template treats "secondary supplementaries" as supplementary."""
    builder = SamBuilder()

    r1, r2 = builder.add_pair(name="x", chrom="chr1", start1=10, start2=30)
    r1_secondary, r2_secondary = builder.add_pair(name="x", chrom="chr1", start1=2, start2=5)
    r1_secondary.is_secondary = True
    r2_secondary.is_secondary = True

    r1_supp, r2_supp = builder.add_pair(name="x", chrom="chr1", start1=2, start2=3)
    r1_supp.is_supplementary = True
    r2_supp.is_supplementary = True

    r1_secondary_supp, r2_secondary_supp = builder.add_pair(
        name="x", chrom="chr1", start1=2, start2=3
    )
    r1_secondary_supp.is_secondary = True
    r2_secondary_supp.is_secondary = True
    r1_secondary_supp.is_supplementary = True
    r2_secondary_supp.is_supplementary = True

    actual = Template.build(
        [
            r1,
            r2,
            r1_secondary,
            r2_secondary,
            r1_supp,
            r2_supp,
            r1_secondary_supp,
            r2_secondary_supp,
        ]
    )
    expected = Template(
        name="x",
        r1=r1,
        r2=r2,
        r1_secondaries=[r1_secondary],
        r2_secondaries=[r2_secondary],
        r1_supplementals=[r1_supp, r1_secondary_supp],
        r2_supplementals=[r2_supp, r2_secondary_supp],
    )
    assert actual == expected


def test_set_tag() -> None:
    builder = SamBuilder()
    template = Template.build(builder.add_pair(chrom="chr1", start1=100, start2=200))

    TAG = "XF"
    VALUE = "value"

    for read in template.all_recs():
        with pytest.raises(KeyError):
            read.get_tag(TAG)

    # test setting
    template.set_tag(TAG, VALUE)
    assert template.r1.get_tag(TAG) == VALUE
    assert template.r2.get_tag(TAG) == VALUE

    # test removal
    template.set_tag(TAG, None)
    for read in template.all_recs():
        with pytest.raises(KeyError):
            read.get_tag(TAG)

    # test tags that aren't two characters
    for bad_tag in ["", "A", "ABC", "ABCD"]:
        with pytest.raises(AssertionError, match="Tags must be 2 characters"):
            template.set_tag(bad_tag, VALUE)


def test_with_aux_alignments() -> None:
    """Test that we add auxiliary alignments as SAM records to a template."""
    secondary: str = "chr9,-104599381,49M,4,0,30;chr3,+170653467,49M,4,0,20;;;"  # with trailing ';'
    supplementary: str = "chr9,104599381,-,39M,50,2"
    builder = SamBuilder()
    rec = builder.add_single(chrom="chr1", start=32)
    rec.set_tag("RX", "ACGT")

    assert list(AuxAlignment.many_from_primary(rec)) == []

    rec.set_tag("SA", supplementary)
    rec.set_tag("XB", secondary)

    actual = Template.build([rec]).with_aux_alignments()
    expected = Template.build([rec] + list(AuxAlignment.many_pysam_from_primary(rec)))

    assert actual == expected
