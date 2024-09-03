from pathlib import Path

import pytest

from fgpyo import sam
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


def test_template_iterator() -> None:
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


def test_template_set_tag() -> None:
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


def test_template_fixmate() -> None:
    builder = SamBuilder(r1_len=100, r2_len=100, base_quality=30)

    # both reads are mapped
    r1, r2 = builder.add_pair(name="q1", chrom="chr1", start1=100, start2=500)
    r1.cigarstring = "80M20S"
    r1.reference_start = 107
    template = Template.build([r1, r2])
    template.fixmate()
    assert r1.get_tag("MC") == "100M"
    assert r2.get_tag("MC") == "80M20S"
    assert r2.next_reference_start == 107

    # only read 1 is mapped
    r1, r2 = builder.add_pair(name="q1", chrom="chr1", start1=100)
    r1.cigarstring = "80M20S"
    r1.reference_start = 107
    template = Template.build([r1, r2])
    template.fixmate()
    with pytest.raises(KeyError):
        r1.get_tag("MC")
    assert r2.get_tag("MC") == "80M20S"
    assert r2.next_reference_start == 107

    # neither reads are mapped
    r1, r2 = builder.add_pair(chrom=sam.NO_REF_NAME)
    r1.cigarstring = "80M20S"
    template = Template.build([r1, r2])
    template.fixmate()
    with pytest.raises(KeyError):
        r1.get_tag("MC")
    with pytest.raises(KeyError):
        r2.get_tag("MC")

    # all supplementary (and not secondard) records should be updated
    r1, r2 = builder.add_pair(name="q1", chrom="chr1", start1=100, start2=500)
    supp1a = builder.add_single(name="q1", read_num=1, chrom="chr1", start=101, supplementary=True)
    supp1b = builder.add_single(name="q1", read_num=1, chrom="chr1", start=102, supplementary=True)
    supp2a = builder.add_single(name="q1", read_num=2, chrom="chr1", start=501, supplementary=True)
    supp2b = builder.add_single(name="q1", read_num=2, chrom="chr1", start=502, supplementary=True)
    sec1 = builder.add_single(name="q1", read_num=1, chrom="chr1", start=1001, secondary=True)
    sec2 = builder.add_single(name="q1", read_num=2, chrom="chr1", start=1002, secondary=True)
    r1.cigarstring = "80M20S"
    r1.reference_start = 107
    template = Template.build([r1, r2, supp1a, supp1b, supp2a, supp2b, sec1, sec2])
    template.fixmate()
    assert r1.get_tag("MC") == "100M"
    assert supp1a.get_tag("MC") == "100M"
    assert supp1b.get_tag("MC") == "100M"
    with pytest.raises(KeyError):
        sec1.get_tag("MC")
    assert r2.get_tag("MC") == "80M20S"
    assert supp2a.get_tag("MC") == "80M20S"
    assert supp2b.get_tag("MC") == "80M20S"
    with pytest.raises(KeyError):
        sec2.get_tag("MC")
    assert r2.next_reference_start == 107
    assert supp2a.next_reference_start == 107
    assert supp2b.next_reference_start == 107
    assert sec2.next_reference_start == -1
