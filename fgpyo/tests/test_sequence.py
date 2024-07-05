"""Tests for :py:mod:`~fgpyo.sequence`"""

import pytest

from fgpyo.sequence import gc_content
from fgpyo.sequence import longest_hp_length
from fgpyo.sequence import reverse_complement


@pytest.mark.parametrize(
    "bases, expected_rev_comp",
    [
        ("", ""),
        ("AATTCCGGaattccgg", "ccggaattCCGGAATT"),
        ("ACGTN", "NACGT"),
    ],
)
def test_reverse_complement(bases: str, expected_rev_comp: str) -> None:
    assert reverse_complement(bases) == expected_rev_comp

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


@pytest.mark.parametrize(
    "bases, expected_gc_content",
    [
        ("ATATATATTATATA", 0.0),
        ("GCGCGCGCGCGCG", 1.0),
        ("ACGT", 0.5),
        ("", 0.0),
        ("ACGTN", 0.4),
        ("acGTN", 0.4),  # mixed case
        ("ggcc", 1.0),
    ],
)
def test_gc_content(bases: str, expected_gc_content: float) -> None:
    assert gc_content(bases) == expected_gc_content
