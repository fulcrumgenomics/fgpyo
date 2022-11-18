"""Tests for :py:mod:`~fgpyo.sequence`"""

import pytest

from fgpyo.sequence import reverse_complement


def test_reverse_complement() -> None:
    assert reverse_complement("") == ""
    assert reverse_complement("AATTCCGGaattccgg") == "ccggaattCCGGAATT"
    assert reverse_complement("ACGTN") == "NACGT"

    with pytest.raises(KeyError):
        reverse_complement("ACGT.GAT")

    with pytest.raises(KeyError):
        reverse_complement("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
