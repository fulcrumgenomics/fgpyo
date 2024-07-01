"""Tests for :py:mod:`~fgpyo.sequence`"""

import pytest

from fgpyo.sequence import gc_content
from fgpyo.sequence import reverse_complement


def test_reverse_complement() -> None:
    assert reverse_complement("") == ""
    assert reverse_complement("AATTCCGGaattccgg") == "ccggaattCCGGAATT"
    assert reverse_complement("ACGTN") == "NACGT"

    with pytest.raises(KeyError):
        reverse_complement("ACGT.GAT")

    with pytest.raises(KeyError):
        reverse_complement("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def test_gc_content() -> None:
    assert gc_content("ATATATATTATATA") == 0.0
    assert gc_content("GCGCGCGCGCGCG") == 1.0
    assert gc_content("ACGT") == 0.5
    assert gc_content("") == 0.0
    assert gc_content("ACGTN") == 0.4
