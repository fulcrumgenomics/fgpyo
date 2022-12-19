"""Basic tests for reference_set_builder"""

from pathlib import Path

from fgpyo.fasta.reference_set_builder import FastaBuilder


def test_add_seq_to_record() -> None:
    builder = FastaBuilder()
    builder.add("chr1").add("AAAAAAAAAA", 10).add("NNNNNNNNNN", 10)
    builder.add("chr10").add("GGGGGGGGGG", 10)
    builder.to_file(Path("some.fasta"))
    assert len(builder.__getitem__("chr1")._bases) == 200
    assert len(builder.__getitem__("chr10")._bases) == 100
