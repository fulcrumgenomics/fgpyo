"""Tests for :py:mod:`~fgpyo.sequence`"""

import pytest

from fgpyo.sequence import longest_hp_length
from fgpyo.sequence import reverse_complement


def test_reverse_complement() -> None:
    assert reverse_complement("") == ""
    assert reverse_complement("AATTCCGGaattccgg") == "ccggaattCCGGAATT"
    assert reverse_complement("ACGTN") == "NACGT"

    with pytest.raises(KeyError):
        reverse_complement("ACGT.GAT")

    with pytest.raises(KeyError):
        reverse_complement("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def test_homopolymer() -> None:
    assert longest_hp_length("") == 0
    assert longest_hp_length("A") == 1
    assert longest_hp_length("AAAA") == 4
    assert longest_hp_length("ACTACGATTTTTACGAT") == 5
    assert longest_hp_length("ACTACGATTTTTACGAT") == 5
    assert longest_hp_length("TTTTACTACGAACGAGTTTTT") == 5
