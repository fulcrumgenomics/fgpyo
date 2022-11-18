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
