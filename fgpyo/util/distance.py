"""
These functions are included for convenience.
If you are performing many distance calculations, using a C based method is preferable.
ex. https://pypi.org/project/Distance/
"""
from typing import List


def hamming(string1: str, string2: str) -> int:
    """
    Calculates hamming distance between two strings. Strings must be of equal lengths.

    Args:
        string1: first string for comparison
        string2: second string for comparison

    Raises ValueError if strings are of different lengths
    """
    if len(string1) != len(string2):
        raise ValueError(
            "Hamming distance requires two strings of equal lengths."
            f"Received {string1} and {string2}."
        )
    return sum([string1[i] != string2[i] for i in range(len(string1))])


def levenshtein(string1: str, string2: str) -> int:
    """
    Calculates levenshtein distance between two strings.

    Args:
        string1: first string for comparison
        string2: second string for comparison

    """
    N: int = len(string1)
    M: int = len(string2)
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
                matrix[i][j] = matrix[i + 1][j + 1] # No Operation
            else:
                matrix[i][j] = 1 + min(
                    matrix[i + 1][j],  # Deletion
                    matrix[i][j + 1],  # Insertion
                    matrix[i + 1][j + 1],  # Substitution
                )
    return matrix[0][0]
