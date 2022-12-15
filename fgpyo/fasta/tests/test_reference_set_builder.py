"""Basic tests for reference_set_builder"""

import pytest

from fgpyo import fasta
from fgpyo.fasta.reference_set_builder import ReferenceBuilder
from fgpyo.fasta.reference_set_builder import ReferenceSetBuilder


def test_add_seq_to_record() -> None:
    builder = ReferenceSetBuilder()
    builder.add("chr1").add("AAAAAAAAAA", 10)
    assert len(builder.REF_BUILDERS[0].sequences) == 100
