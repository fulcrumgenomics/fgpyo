import pytest

from fgpyo.sam import Cigar

cigar = Cigar.from_cigarstring("1M4D45N37X23I11=")


@pytest.mark.parametrize("index", range(-len(cigar.elements), len(cigar.elements)))
def test_direct_access(index: int) -> None:
    assert cigar[index] == cigar.elements[index]
    assert cigar[index:] == cigar.elements[index:]
    assert cigar[:index] == cigar.elements[:index]
    assert cigar[index:-1] == cigar.elements[index:-1]


@pytest.mark.parametrize(
    "index",
    [
        -7,
        -100,
        6,
        100,
    ],
)
def test_bad_index_raises_index_error(index: int) -> None:
    with pytest.raises(IndexError):
        cigar[index]


@pytest.mark.parametrize("index", ["a", "b", (1, 2)])
def test_bad_index_raises_type_error(index: int) -> None:
    with pytest.raises(TypeError):
        cigar[index]
