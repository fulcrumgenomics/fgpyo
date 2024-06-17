import timeit

# TODO: Remove Timing notes
# 0.297, 0.285
timeit.timeit("len(list(filter(lambda xy: xy[0] != xy[1], zip('ABC', 'CBA'))))", number=1000000)
# 0.152, 0.153
timeit.timeit("sum(['ABC'[i] != 'CBA'[i] for i in range(len('CBA'))])", number=1000000)
# 0.299, 0.299
timeit.timeit("sum(char1 != char2 for char1, char2 in zip('ABC', 'CBA', strict=True))", number=1000000)

def hamming(string1: str, string2: str) -> int:
    """
    Calculates hamming distance between two strings. Strings must be of equal lengths.

    Args:
        string1: first string for comparison
        string2: second string for comparison


    """
    if len(string1) != len(string2):
        raise ValueError("Hamming distance requires two strings of equal lengths. Received {string1} and {string2}.")
    return sum([string1[i] != string2[i] for i in range(len(string1))])


def levenshtein(str1: str, str2: str):
    """"""
    0

