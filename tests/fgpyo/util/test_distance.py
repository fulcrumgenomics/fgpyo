import pytest

from fgpyo.util.distance import hamming


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
    ],
)
def test_hamming(string1: str, string2: str, hamming_distance: int):
    assert hamming(string1, string2) == hamming_distance


@pytest.mark.parametrize(
    "string1, string2",
    [
        ("", "A"),
        ("AB", "ABC"),
        ("A", ""),
    ],
)
def test_hamming_with_invalid_strings(string1: str, string2: str):
    with pytest.raises(ValueError):
        hamming(string1, string2)
