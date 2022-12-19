"""Basic tests for reference_set_builder"""

from fgpyo.fasta.fasta_builder import FastaBuilder


def test_add_bases_to_existing_contig() -> None:
    builder = FastaBuilder()
    contig = builder.add("chr1").add("AAAAAAAAAA", 10).add("NNNNNNNNNN", 10)
    contig.add("TTTTTTTTTT", 10)
    assert len(builder.__getitem__("chr1")._bases) == 300
