import pytest

from fgpyo.sam import Cigar

cigar = Cigar.from_cigarstring("1M4D45N37X23I11=")


def test_cigar_length_exists():
    assert len(cigar) == len(cigar.elements)


@pytest.mark.parametrize("index", range(-len(cigar), len(cigar)))
def test_direct_access(index: int):
    assert cigar[index] == cigar.elements[index]
    assert cigar[index:] == cigar.elements[index:]
    assert cigar[:index] == cigar.elements[:index]
    assert cigar[index:-1] == cigar.elements[index:-1]
