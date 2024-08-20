"""
# Utility Functions for Manipulating DNA and RNA sequences.

This module contains utility functions for manipulating DNA and RNA sequences.


`levenshtein` and `hamming` functions are included for convenience.
If you are performing many distance calculations, using a C based method is preferable.
ex. https://pypi.org/project/Distance/
"""

from typing import Dict
from typing import List

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
    gc_count = sum(1 for base in bases if base in "CGcg")
    return gc_count / len(bases)


def hamming(string1: str, string2: str) -> int:
    """
    Calculates hamming distance between two strings, case sensitive.
    Strings must be of equal lengths.

    Args:
        string1: first string for comparison
        string2: second string for comparison

    Raises:
        ValueError: If strings are of different lengths.
    """
    if len(string1) != len(string2):
        raise ValueError(
            "Hamming distance requires two strings of equal lengths."
            f"Received {string1} and {string2}."
        )
    return sum([string1[i] != string2[i] for i in range(len(string1))])


def levenshtein(string1: str, string2: str) -> int:
    """
    Calculates levenshtein distance between two strings, case sensitive.

    Args:
        string1: first string for comparison
        string2: second string for comparison

    """
    N: int = len(string1)
    M: int = len(string2)
    if N == 0 or M == 0:
        return max(N, M)
    # Initialize N + 1 x M + 1 matrix with final row/column representing the empty string.
    # Fill in initial values for empty string sub-problem comparisons.
    #   A D C "
    # A - - - 3
    # B - - - 2
    # C - - - 1
    # " 3 2 1 0
    matrix: List[List[int]] = [[int()] * (M + 1) for _ in range(N + 1)]
    for j in range(M + 1):
        matrix[N][j] = M - j
    for i in range(N + 1):
        matrix[i][M] = N - i
    # Fill in matrix from bottom up using previous sub-problem solutions.
    #   A D C "      A D C "      A D C "      A D C "      A D C "
    # A - - - 3    A - - - 3    A - - 2 3    A - 2 2 3    A 1 2 2 3
    # B - - - 2 -> B - - 1 2 -> B - 1 1 2 -> B 2 1 1 2 -> B 2 1 1 2
    # C - - 0 1    C - 1 0 1    C 2 1 0 1    C 2 1 0 1    C 2 1 0 1
    # " 3 2 1 0    " 3 2 1 0    " 3 2 1 0    " 3 2 1 0    " 3 2 1 0
    for i in range(N - 1, -1, -1):
        for j in range(M - 1, -1, -1):
            if string1[i] == string2[j]:
                matrix[i][j] = matrix[i + 1][j + 1]  # No Operation
            else:
                matrix[i][j] = 1 + min(
                    matrix[i + 1][j],  # Deletion
                    matrix[i][j + 1],  # Insertion
                    matrix[i + 1][j + 1],  # Substitution
                )
    return matrix[0][0]


def longest_hp_length(bases: str) -> int:
    """Calculates the length of the longest homopolymer in the input sequence.

    Args:
        bases: the bases over which to compute

    Return:
        the length of the longest homopolymer
    """
    return longest_homopolymer_length(bases=bases)


def longest_homopolymer_length(bases: str) -> int:
    """Calculates the length of the longest homopolymer in the input sequence.

    Args:
        bases: the bases over which to compute

    Return:
        the length of the longest homopolymer
    """
    cur_length: int = 0
    i = 0
    # NB: if we have found a homopolymer of length `min_hp`, then we do not need
    # to examine the last `min_hp` bases since we'll never find a longer one.
    bases_len = len(bases)
    while i < bases_len - cur_length:
        base = bases[i].upper()
        j = i + 1
        while j < bases_len and bases[j].upper() == base:
            j += 1
        cur_length = max(cur_length, j - i)
        # skip over all the bases in the current homopolymer
        i = j
    return cur_length


def longest_dinucleotide_run_length(bases: str) -> int:
    """Number of bases in the longest dinucleotide run in a primer.

    A dinucleotide run is when two nucleotides are repeated in tandem. For example,
    TTGG (length = 4) or AACCAACCAA (length = 10). If there are no such runs, returns 0.

    Args:
        bases: the bases over which to compute

    Return:
        the number of bases in the longest dinuc repeat (NOT the number of repeat units)
    """
    return longest_multinucleotide_run_length(bases=bases, repeat_unit_length=2)


def longest_multinucleotide_run_length(bases: str, repeat_unit_length: int) -> int:
    """Number of bases in the longest multi-nucleotide run.

    A multi-nucleotide run is when N nucleotides are repeated in tandem. For example,
    TTGG (length = 4, N=2) or TAGTAGTAG (length = 9, N = 3). If there are no such runs,
    returns 0.

    Args:
        bases: the bases over which to compute
        repeat_unit_length: the length of the multi-nucleotide repetitive unit (must be > 0)

    Returns:
        the number of bases in the longest multinucleotide repeat (NOT the number of repeat units)
    """
    if repeat_unit_length <= 0:
        raise ValueError(f"repeat_unit_length must be >= 0, found: {repeat_unit_length}")
    elif len(bases) < repeat_unit_length:
        return 0
    elif len(bases) == repeat_unit_length:
        return repeat_unit_length
    elif repeat_unit_length == 1:
        return longest_homopolymer_length(bases=bases)

    best_length: int = 0
    start = 0  # the start index of the current multi-nucleotide run
    while start < len(bases) - 1:
        # get the dinuc bases
        dinuc = bases[start : start + repeat_unit_length].upper()
        # keep going while there are more di-nucs
        end = start + repeat_unit_length
        while end < len(bases) - 1 and dinuc == bases[end : end + repeat_unit_length].upper():
            end += repeat_unit_length
        cur_length = end - start
        # update the longest total run length
        best_length = max(best_length, cur_length)
        # move to the next start
        if cur_length <= repeat_unit_length:  # only one repeat unit found, move the start by 1bp
            start += 1
        else:  # multiple repeats found, skip to the last base of the current run
            start += cur_length - 1

    return best_length
