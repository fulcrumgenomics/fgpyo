"""Basic tests for reference_set_builder"""

from fgpyo.fasta.reference_set_builder import ReferenceSetBuilder


def test_add_seq_to_record() -> None:
    builder = ReferenceSetBuilder()
    builder.add("chr1").add("AAAAAAAAAA", 10).add("NNNNNNNNNN", 10)
    builder.add("chr10").add("GGGGGGGGGG", 10)
    assert len(builder.REF_BUILDERS[0].bases) == 200
    assert len(builder.REF_BUILDERS[1].bases) == 100
