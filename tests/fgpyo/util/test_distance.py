import pytest

from fgpyo.util.distance import hamming
from fgpyo.util.distance import levenshtein


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
