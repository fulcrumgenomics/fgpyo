"""Tests for `~fgpyo.sequence`"""

import pytest

from fgpyo.sequence import gc_content
from fgpyo.sequence import hamming
from fgpyo.sequence import levenshtein
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
