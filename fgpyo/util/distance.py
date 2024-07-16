def hamming(string1: str, string2: str) -> int:
    """
    Calculates hamming distance between two strings. Strings must be of equal lengths.

    Args:
        string1: first string for comparison
        string2: second string for comparison


    """
    if len(string1) != len(string2):
        raise ValueError(
            "Hamming distance requires two strings of equal lengths."
            f"Received {string1} and {string2}."
        )
    return sum([string1[i] != string2[i] for i in range(len(string1))])


def levenshtein(str1: str, str2: str):
    """"""
    0
