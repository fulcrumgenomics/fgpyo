"""Tests for `~fgpyo.sequence`"""

from typing import List
from typing import Tuple

import pytest

from fgpyo.sequence import gc_content
from fgpyo.sequence import hamming
from fgpyo.sequence import levenshtein
from fgpyo.sequence import longest_dinucleotide_run_length
from fgpyo.sequence import longest_homopolymer_length
from fgpyo.sequence import longest_hp_length
from fgpyo.sequence import longest_multinucleotide_run_length
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

    # check unicode character is caught, not just ascii. The unicode symbol Omega is included:
    with pytest.raises(KeyError):
        reverse_complement(b"ATCG\xce\xa9ATCG".decode())


@pytest.mark.parametrize(
    "bases, expected_hp_len",
    [
        ("", 0),
        ("A", 1),
        ("AAAA", 4),
        ("ccgTATGC", 2),
        ("ACTACGATTTTTACGAT", 5),
        ("ACTACGATTTTTACGAT", 5),
        ("TTTTACTACGAACGAGTTTTT", 5),
    ],
)
def test_homopolymer(bases: str, expected_hp_len: int) -> None:
    assert longest_hp_length(bases) == expected_hp_len
    assert longest_homopolymer_length(bases) == expected_hp_len


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
    "string1, string2, hamming_distance",
    [
        ("", "", 0),
        ("AAA", "AAA", 0),
        ("ABC", "ABC", 0),
        ("AAC", "ABC", 1),
        ("AAC", "BBC", 2),
        ("CBA", "ABC", 2),
        ("AAA", "BBB", 3),
        ("AbC", "ABC", 1),
        ("abc", "ABC", 3),
        ("hamming", "hamning", 1),
    ],
)
def test_hamming(string1: str, string2: str, hamming_distance: int) -> None:
    assert hamming(string1, string2) == hamming_distance


@pytest.mark.parametrize(
    "string1, string2",
    [
        ("", "A"),
        ("AB", "ABC"),
        ("A", ""),
    ],
)
def test_hamming_with_invalid_strings(string1: str, string2: str) -> None:
    with pytest.raises(ValueError):
        hamming(string1, string2)


@pytest.mark.parametrize(
    "string1, string2, levenshtein_distance",
    [
        ("", "", 0),
        ("AAA", "AAA", 0),
        ("ABC", "ABC", 0),
        ("AAC", "ABC", 1),
        ("AAC", "BBC", 2),
        ("CBA", "ABC", 2),
        ("AAA", "BBB", 3),
        ("AbC", "ABC", 1),
        ("abc", "ABC", 3),
        ("AB", "ABC", 1),
        ("ABC", "AB", 1),
        ("CC", "AAA", 3),
        ("CAC", "AAA", 2),
        ("lenvestein", "levenshtein", 3),
    ],
)
def test_levenshtein_dynamic(string1: str, string2: str, levenshtein_distance: int) -> None:
    assert levenshtein(string1, string2) == levenshtein_distance


MULTINUCLEOTIDE_TEST_CASES: List[Tuple[str, int, int]] = [
    ("", 2, 0),
    ("", 1, 0),
    ("A", 1, 1),
    ("ccgTATGC", 1, 2),
    ("A", 2, 0),
    ("ACGT", 2, 2),
    ("AACCGGTT", 2, 2),
    ("TTTTCCCGGA", 2, 4),
    ("ACCGGGTTTT", 2, 4),
    ("GTGTGTAAAA", 2, 6),
    ("GTGTGTGAAAA", 2, 6),
    ("GTGTGTACACACAC", 2, 8),
    ("GTGTGTGACACACAC", 2, 8),
    ("AAACTCTCTCGG", 2, 6),
    ("AACTCTCTCGGG", 2, 6),
    ("TGTATATATA", 2, 8),
    ("TGTATATATAC", 2, 8),
    ("TGATATATATC", 2, 8),
    ("TGATATATAC", 2, 6),
    ("TAGTAGTAG", 3, 9),
    ("TATAGTAGTAGTA", 3, 9),
    ("TACGTACGTACTG", 4, 8),
    ("TAGTAGTAGTAG", 3, 12),
    ("TAGTAGTAGTAG", 6, 12),
    ("TAGTAGTAGTAG", 12, 12),
    ("AACCGGTT", 1, 2),
    ("AACCGGTT", 3, 3),
    ("TAGTAGTAGTAG", 5, 5),
    ("TAGTAGTAGTAG", 7, 7),
    ("TTTAAAAAAAAAATTT", 5, 10),
    ("ACGACCATATatatatatatGC", 2, 14),
    ("ACGACCATATatatatatatATGC", 2, 16),
    ("ttgaTtaCaGATTACAgattacacc", 7, 21),
]

DINUCLEOTIDE_TEST_CASES: List[Tuple[str, int]] = [
    (bases, expected_length)
    for bases, repeat_unit_length, expected_length in MULTINUCLEOTIDE_TEST_CASES
    if repeat_unit_length == 2
]


@pytest.mark.parametrize("bases, expected_length", DINUCLEOTIDE_TEST_CASES)
def test_longest_dinucleotide_run_length(bases: str, expected_length: int) -> None:
    assert expected_length == longest_dinucleotide_run_length(bases=bases)


@pytest.mark.parametrize("bases, repeat_unit_length, expected_length", MULTINUCLEOTIDE_TEST_CASES)
def test_longest_multinucleotide_run_length(
    bases: str, repeat_unit_length: int, expected_length: int
) -> None:
    assert expected_length == 0 or expected_length % repeat_unit_length == 0
    assert expected_length == longest_multinucleotide_run_length(
        bases, repeat_unit_length=repeat_unit_length
    )


def test_longest_multinucleotide_run_length_raises() -> None:
    with pytest.raises(ValueError, match="repeat_unit_length must be >= 0"):
        longest_multinucleotide_run_length(bases="GATTACA", repeat_unit_length=0)
