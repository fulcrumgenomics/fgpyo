"""
Utility Functions for Manipulating DNA and RNA sequences.
---------------------------------------------------------

This module contains utility functions for manipulating DNA and RNA sequences.

"""

from typing import Dict

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


def longest_hp_length(bases: str) -> int:
    """Calculates the length of the longest homopolymer in the input sequence."""
    max_hp = 0
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


def gc_content(bases: str) -> float:
    """Calculates the fraction of G and C bases in a sequence."""
    if len(bases) == 0:
        return 0
    gc_count = sum(1 for base in bases if base == "C" or base == "G" or base == "c" or base == "g")
    return gc_count / len(bases)
