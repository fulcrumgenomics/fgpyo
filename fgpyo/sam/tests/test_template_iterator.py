from fgpyo.sam import Template
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
