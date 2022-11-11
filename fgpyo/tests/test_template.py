from samwell.sam.sambuilder import SamBuilder

from fgpyo.template import Template


def test_init_empty() -> None:
    template = Template()
    assert template.r1 is None
    assert len([t for t in template.r1_supplementals]) == 0
    assert len([t for t in template.r1_secondaries]) == 0


def test_init_values() -> None:
    sam_builder: SamBuilder = SamBuilder()
    sam_builder.add_pair(name="x", chrom="chr1", start1=1, start2=2)
    r1 = sam_builder.to_sorted_list()[0]
    r2 = sam_builder.to_sorted_list()[1]
    template = Template(
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
    sam_builder = SamBuilder()

    # Contiguous series of alignments for one template
    # Primary alignment
    sam_builder.add_pair(name="q1", chrom="chr1", start1=1, start2=2)
    # Two supplementary alignments for r1 and r2 respectively
    supp1 = sam_builder.add_pair(name="q1", chrom="chr1", start1=1)
    supp2 = sam_builder.add_pair(name="q1", chrom="chr1", start2=2)
    supp1[0].is_supplementary = True
    supp2[1].is_supplementary = True
    # A secondary alignment
    sec1 = sam_builder.add_pair(name="q1", chrom="chr1", start1=1)
    sec1[0].is_secondary = True
    # Another supplementary alignment
    supp3 = sam_builder.add_pair(name="q1", chrom="chr1", start1=1)
    supp3[0].is_supplementary = True
    # Another secondary alignment
    sec2 = sam_builder.add_pair(name="q1", chrom="chr1", start2=2)
    sec2[1].is_secondary = True

    # Another template with primary alignment for r2 only
    sam_builder.add_pair(name="q2", chrom="chr1", start2=2)

    # Another supplementary alignment for template q1; because we don't sort this should be added
    # to a new template
    supp4 = sam_builder.add_pair(name="q1", chrom="chr1", start2=1)
    supp4[1].is_supplementary = True

    # Build templates
    templates = [t for t in Template.to_templates(sam_builder.to_unsorted_list())]
    assert len(templates) == 3
    template1, template2, template3 = templates

    # Check template 1
    assert template1.r1.qname == "q1"
    assert template1.r2.qname == "q1"
    assert len(template1.r1_supplementals) == 2
    assert len(template1.r2_supplementals) == 1
    assert len(template1.r1_secondaries) == 1
    assert len(template1.r2_secondaries) == 1

    # Check template 2
    assert template2.r2.qname == "q2"
    assert len(template2.r1_supplementals) == 0
    assert len(template2.r2_supplementals) == 0
    assert len(template2.r1_secondaries) == 0
    assert len(template2.r2_secondaries) == 0

    # Check template 3
    assert template3.r1 is None
    assert template3.r2 is None
    assert len(template3.r1_supplementals) == 0
    assert len(template3.r2_supplementals) == 1
    assert template3.r2_supplementals[0].qname == "q1"
    assert len(template3.r1_secondaries) == 0
    assert len(template3.r2_secondaries) == 0
