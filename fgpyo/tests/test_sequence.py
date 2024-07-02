"""Tests for :py:mod:`~fgpyo.sequence`"""

import pytest

from fgpyo.sequence import gc_content
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
    "bases, expected_gc_content",
    [
        ("ATATATATTATATA", 0.0),
        ("GCGCGCGCGCGCG", 1.0),
        ("ACGT", 0.5),
        ("", 0.0),
        ("ACGTN", 0.4),
        ("acGTN", 0.4), # mixed case
        ("ggcc", 1.0)
    ],
)
def test_gc_content(bases: str, expected_gc_content: float) -> None:
    assert gc_content(bases) == expected_gc_content