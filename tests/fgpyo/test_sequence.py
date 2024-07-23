"""Tests for `~fgpyo.sequence`"""

import pytest

from fgpyo.sequence import gc_content, longest_multinucleotide_run_length
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


@pytest.mark.parametrize(
    "bases, n, expected_length",
    [
        ("", 2, 0),
        ("", 1, 0),
        ("A", 1, 1),
        ("A", 2, 0),
        ("ACGT", 2, 2),
        ("AACCGGTT",2,  2),
        ("TTTTCCCGGA",2,  4),
        ("ACCGGGTTTT",2,  4),
        ("GTGTGTAAAA", 2, 6),
        ("GTGTGTGAAAA",2,  6),
        ("GTGTGTACACACAC",2,  8),
        ("GTGTGTGACACACAC",2,  8),
        ("AAACTCTCTCGG", 2, 6),
        ("AACTCTCTCGGG", 2, 6),
        ("TGTATATATA", 2, 8),
        ("TGTATATATAC",2,  8),
        ("TGATATATATC",2,  8),
        ("TGATATATAC", 2, 6),
        ("TAGTAGTAG", 3, 9),
        ("TATAGTAGTAGTA", 3, 9),
        ("TACGTACGTACTG", 4, 8),
        ("TAGTAGTAGTAG", 3, 12),
        ("TAGTAGTAGTAG", 6, 12),
        ("TAGTAGTAGTAG", 12, 12),
    ],
)
def test_longest_multinucleotide_run_length(bases: str, n: int, expected_length: int) -> None:
    assert expected_length == 0 or expected_length % n == 0
    assert longest_multinucleotide_run_length(bases, n=n) == expected_length
