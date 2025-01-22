from pathlib import Path

import pytest

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


def test_template_set_mate_info() -> None:
    """Test that Template set_mate_info fixes up all records in a template."""
    builder = SamBuilder()

    r1, r2 = builder.add_pair(name="x", chrom="chr1", start1=200, start2=300)
    r1_secondary = builder.add_single(name="x", read_num=1, chrom="chr1", start=2)
    r2_secondary = builder.add_single(name="x", read_num=2, chrom="chr1", start=5)
    r1_secondary.is_secondary = True
    r2_secondary.is_secondary = True

    r1_supp = builder.add_single(name="x", read_num=1, chrom="chr1", start=4)
    r2_supp = builder.add_single(name="x", read_num=2, chrom="chr1", start=5)
    r1_supp.is_supplementary = True
    r2_supp.is_supplementary = True

    r1_secondary_supp = builder.add_single(name="x", read_num=1, chrom="chr1", start=6)
    r2_secondary_supp = builder.add_single(name="x", read_num=2, chrom="chr1", start=7)
    r1_secondary_supp.is_secondary = True
    r2_secondary_supp.is_secondary = True
    r1_secondary_supp.is_supplementary = True
    r2_secondary_supp.is_supplementary = True

    template = Template.build(
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

    template.set_mate_info()

    # Assert the state of both the R1 and R2 alignments
    for rec in (template.r1, template.r2):
        assert rec.reference_id == builder.header.get_tid("chr1")
        assert rec.reference_name == "chr1"
        assert rec.next_reference_id == builder.header.get_tid("chr1")
        assert rec.next_reference_name == "chr1"
        assert rec.has_tag("MC")
        assert rec.get_tag("MC") == "100M"
        assert rec.has_tag("MQ")
        assert rec.get_tag("MQ") == 60
        assert rec.has_tag("ms")
        assert rec.get_tag("ms") == 3000
        assert rec.is_proper_pair is True

    assert template.r1.reference_start == 200
    assert template.r1.next_reference_start == 300
    assert template.r2.reference_start == 300
    assert template.r2.next_reference_start == 200
    assert template.r1.template_length == 200
    assert template.r2.template_length == -200
    assert template.r1.is_forward is True
    assert template.r2.is_reverse is True
    assert template.r1.mate_is_reverse is True
    assert template.r2.mate_is_forward is True

    # Assert the state of the two secondary non-supplementary alignments
    assert template.r1_secondaries[0].reference_id == builder.header.get_tid("chr1")
    assert template.r1_secondaries[0].reference_name == "chr1"
    assert template.r1_secondaries[0].reference_start == 2
    assert template.r1_secondaries[0].next_reference_id == template.r2.reference_id
    assert template.r1_secondaries[0].next_reference_name == template.r2.reference_name
    assert template.r1_secondaries[0].next_reference_start == template.r2.reference_start
    assert template.r1_secondaries[0].has_tag("MC")
    assert template.r1_secondaries[0].get_tag("MC") == template.r2.cigarstring
    assert template.r1_secondaries[0].has_tag("MQ")
    assert template.r1_secondaries[0].get_tag("MQ") == template.r2.mapping_quality
    assert template.r1_secondaries[0].has_tag("ms")
    assert template.r1_secondaries[0].get_tag("ms") == 3000
    assert template.r1_secondaries[0].template_length == 0
    assert template.r1_secondaries[0].is_proper_pair is False
    assert template.r1_secondaries[0].is_forward is True
    assert template.r1_secondaries[0].mate_is_forward is template.r2.is_forward

    assert template.r2_secondaries[0].reference_id == builder.header.get_tid("chr1")
    assert template.r2_secondaries[0].reference_name == "chr1"
    assert template.r2_secondaries[0].reference_start == 5
    assert template.r2_secondaries[0].next_reference_id == template.r1.reference_id
    assert template.r2_secondaries[0].next_reference_name == template.r1.reference_name
    assert template.r2_secondaries[0].next_reference_start == template.r1.reference_start
    assert template.r2_secondaries[0].has_tag("MC")
    assert template.r2_secondaries[0].get_tag("MC") == template.r1.cigarstring
    assert template.r2_secondaries[0].has_tag("MQ")
    assert template.r2_secondaries[0].get_tag("MQ") == template.r1.mapping_quality
    assert template.r2_secondaries[0].has_tag("ms")
    assert template.r2_secondaries[0].get_tag("ms") == 3000
    assert template.r2_secondaries[0].template_length == 0
    assert template.r2_secondaries[0].is_proper_pair is False
    assert template.r2_secondaries[0].is_forward is True
    assert template.r2_secondaries[0].mate_is_forward is template.r1.is_forward

    # Assert the state of the two non-secondary supplemental alignments
    assert template.r1_supplementals[0].reference_id == builder.header.get_tid("chr1")
    assert template.r1_supplementals[0].reference_name == "chr1"
    assert template.r1_supplementals[0].reference_start == 4
    assert template.r1_supplementals[0].next_reference_id == template.r2.reference_id
    assert template.r1_supplementals[0].next_reference_name == template.r2.reference_name
    assert template.r1_supplementals[0].next_reference_start == template.r2.reference_start
    assert template.r1_supplementals[0].has_tag("MC")
    assert template.r1_supplementals[0].get_tag("MC") == template.r2.cigarstring
    assert template.r1_supplementals[0].has_tag("MQ")
    assert template.r1_supplementals[0].get_tag("MQ") == template.r2.mapping_quality
    assert template.r1_supplementals[0].has_tag("ms")
    assert template.r1_supplementals[0].get_tag("ms") == 3000
    assert template.r1_supplementals[0].template_length == 200
    assert template.r1_supplementals[0].is_proper_pair is True
    assert template.r1_supplementals[0].is_forward is True
    assert template.r1_supplementals[0].mate_is_forward is template.r2.is_forward

    assert template.r2_supplementals[0].reference_id == builder.header.get_tid("chr1")
    assert template.r2_supplementals[0].reference_name == "chr1"
    assert template.r2_supplementals[0].reference_start == 5
    assert template.r2_supplementals[0].next_reference_id == template.r1.reference_id
    assert template.r2_supplementals[0].next_reference_name == template.r1.reference_name
    assert template.r2_supplementals[0].next_reference_start == template.r1.reference_start
    assert template.r2_supplementals[0].has_tag("MC")
    assert template.r2_supplementals[0].get_tag("MC") == template.r1.cigarstring
    assert template.r2_supplementals[0].has_tag("MQ")
    assert template.r2_supplementals[0].get_tag("MQ") == template.r1.mapping_quality
    assert template.r2_supplementals[0].has_tag("ms")
    assert template.r2_supplementals[0].get_tag("ms") == 3000
    assert template.r2_supplementals[0].template_length == -200
    assert template.r2_supplementals[0].is_proper_pair is True
    assert template.r2_supplementals[0].is_forward is True
    assert template.r2_supplementals[0].mate_is_forward is template.r1.is_forward

    # Assert the state of the two secondary supplemental alignments
    assert template.r1_supplementals[1].reference_id == builder.header.get_tid("chr1")
    assert template.r1_supplementals[1].reference_name == "chr1"
    assert template.r1_supplementals[1].reference_start == 6
    assert template.r1_supplementals[1].next_reference_id == template.r2.reference_id
    assert template.r1_supplementals[1].next_reference_name == template.r2.reference_name
    assert template.r1_supplementals[1].next_reference_start == template.r2.reference_start
    assert template.r1_supplementals[1].has_tag("MC")
    assert template.r1_supplementals[1].get_tag("MC") == template.r2.cigarstring
    assert template.r1_supplementals[1].has_tag("MQ")
    assert template.r1_supplementals[1].get_tag("MQ") == template.r2.mapping_quality
    assert template.r1_supplementals[1].has_tag("ms")
    assert template.r1_supplementals[1].get_tag("ms") == 3000
    assert template.r1_supplementals[1].template_length == 0
    assert template.r1_supplementals[1].is_proper_pair is False
    assert template.r1_supplementals[1].is_forward is True
    assert template.r1_supplementals[1].mate_is_forward is template.r2.is_forward

    assert template.r2_supplementals[1].reference_id == builder.header.get_tid("chr1")
    assert template.r2_supplementals[1].reference_name == "chr1"
    assert template.r2_supplementals[1].reference_start == 7
    assert template.r2_supplementals[1].next_reference_id == template.r1.reference_id
    assert template.r2_supplementals[1].next_reference_name == template.r1.reference_name
    assert template.r2_supplementals[1].next_reference_start == template.r1.reference_start
    assert template.r2_supplementals[1].has_tag("MC")
    assert template.r2_supplementals[1].get_tag("MC") == template.r1.cigarstring
    assert template.r2_supplementals[1].has_tag("MQ")
    assert template.r2_supplementals[1].get_tag("MQ") == template.r1.mapping_quality
    assert template.r2_supplementals[1].has_tag("ms")
    assert template.r2_supplementals[1].get_tag("ms") == 3000
    assert template.r2_supplementals[1].template_length == 0
    assert template.r2_supplementals[1].is_proper_pair is False
    assert template.r2_supplementals[1].is_forward is True
    assert template.r2_supplementals[1].mate_is_forward is template.r1.is_forward
