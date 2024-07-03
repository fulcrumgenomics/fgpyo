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


@pytest.mark.parametrize(
    "bases, expected_hp_len",
    [
        ("", 0),
        ("A", 1),
        ("AAAA", 4),
        ("ACTACGATTTTTACGAT", 5),
        ("ACTACGATTTTTACGAT", 5),
        ("TTTTACTACGAACGAGTTTTT", 5),
    ],
)
def test_homopolymer(bases: str, expected_hp_len: int) -> None:
    assert longest_hp_length(bases) == expected_hp_len
