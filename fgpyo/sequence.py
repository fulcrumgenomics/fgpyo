"""
# Utility Functions for Manipulating DNA and RNA sequences.

This module contains utility functions for manipulating DNA and RNA sequences.
"""

from typing import Dict
from typing import Optional

_COMPLEMENTS: Dict[str, str] = {
    # Discrete bases
    "A": "T",
    "C": "G",
    "G": "C",
    "T": "A",
    "U": "A",
    # IUPAC codes that represent two bases
    "M": "K",
    "K": "M",
    "R": "Y",
    "Y": "R",
    "W": "S",
    "S": "W",
    # IUPAC codes that represent three bases
    "B": "V",
    "V": "B",
    "H": "D",
    "D": "H",
    # IUPAC universal code
    "N": "N",
    # Discrete bases
    "a": "t",
    "c": "g",
    "g": "c",
    "t": "a",
    "u": "a",
    # IUPAC codes that represent two bases
    "m": "k",
    "k": "m",
    "r": "y",
    "y": "r",
    "w": "s",
    "s": "w",
    # IUPAC codes that represent three bases
    "b": "v",
    "v": "b",
    "h": "d",
    "d": "h",
    # IUPAC universal code
    "n": "n",
}


def complement(base: str) -> str:
    """Returns the complement of any base."""
    if len(base) != 1:
        raise ValueError(f"complement() may only be called with 1-character strings: {base}")
    else:
        return _COMPLEMENTS[base]


def reverse_complement(bases: str) -> str:
    """Reverse complements a base sequence.

    Arguments:
        bases: the bases to be reverse complemented.

    Returns:
        the reverse complement of the provided base string
    """
    return "".join([_COMPLEMENTS[b] for b in bases[::-1]])


def gc_content(bases: str) -> float:
    """Calculates the fraction of G and C bases in a sequence."""
    if len(bases) == 0:
        return 0
    gc_count = sum(1 for base in bases if base == "C" or base == "G" or base == "c" or base == "g")
    return gc_count / len(bases)


def longest_hp_length(bases: str, _max_hp: Optional[int] = None) -> int:
    """Calculates the length of the longest homopolymer in the input sequence."""
    # NB: _max_hp is a private parameter used by longest_multinucleotide_run_length when we want
    # to search for homopolymer run lengths of at least _max_hp
    max_hp = 0 if _max_hp is None else _max_hp
    i = 0
    # NB: if we have found a homopolymer of length `max_hp`, then we do not need
    # to examine the last `max_hp` bases since we'll never find a longer one.
    bases_len = len(bases)
    while i < bases_len - max_hp:
        base = bases[i]
        j = i + 1
        while j < bases_len and bases[j] == base:
            j += 1
        max_hp = max(max_hp, j - i)
        # skip over all the bases in the current homopolymer
        i = j
    return max_hp


def longest_dinucleotide_run_length(bases: str) -> int:
    """Number of bases in the longest dinucleotide run in a primer.

    A dinucleotide run is when two nucleotides are repeated in tandem. For example,
    TTGG (length = 4) or AACCAACCAA (length = 10). If there are no such runs, returns 0."""

    best_length: int = 0

    start = 0  # the start index of the current dinucleotide run
    while start < len(bases) - 1:
        # get the dinuc bases
        first_base = bases[start]
        second_base = bases[start + 1]
        # keep going while there are more di-nucs
        end = start + 2
        while end < len(bases) - 1 and bases[end] == first_base and bases[end + 1] == second_base:
            end += 2
        # update the longest total run length
        best_length = max(best_length, end - start)
        # skip to the last base of the current run
        start += end - start - 1

    return best_length


def longest_multinucleotide_run_length(bases: str, n: int) -> int:
    """Number of bases in the longest multi-nucleotide run.

    A multi-nucleotide run is when N nucleotides are repeated in tandem. For example,
    TTGG (length = 4, N=2) or TAGTAGTAG (length = 9, N = 3). If there are no such runs,
    returns 0."""

    if len(bases) < n:
        return 0
    elif len(bases) == n:
        return len(bases)
    elif n == 1:
        return longest_hp_length(bases=bases)
    elif n == 2:
        return longest_dinucleotide_run_length(bases=bases)

    best_length: int = 0
    for k in range(n):
        # split the bases into groups of <n> bases, such that there are ~`len(bases) / n` items
        cur = [bases[i : i + n] for i in range(k, len(bases) - k, n)]
        # find the longest run of identical items
        cur_length = longest_hp_length(cur, _max_hp=best_length)  # type: ignore
        # update the current longest run of identical items
        best_length = max(best_length, cur_length)
    # since each "item" contains "n" bases, we must multiply by "n"
    best_length *= n
    return best_length
