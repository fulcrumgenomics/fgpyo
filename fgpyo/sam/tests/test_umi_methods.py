import pytest

from fgpyo.sam import _is_valid_umi
from fgpyo.sam import copy_umi_from_read_name
from fgpyo.sam import extract_umis_from_read_name
from fgpyo.sam.builder import SamBuilder


@pytest.mark.parametrize(
    "umi,validity",
    [
        ("ACGTN", True),
        ("rACGTN", False),
        ("+ACGTN", False),
        ("-ACGTN", False),
        ("BXCYF", False),
    ],
)
def test_is_valid_umi(umi: str, validity: bool) -> None:
    """Test that we can detect valid UMIs."""

    assert _is_valid_umi(umi) is validity


@pytest.mark.parametrize(
    "read_name,umi",
    [
        ("abc:ACGT", "ACGT"),
        ("abc:def:ghi:ACGT", "ACGT"),
        ("abc:def:ghi:rACGT", "ACGT"),
        ("abc:def:ghi:rACGT+CAGA", "ACGT-CAGA"),
        ("abc:def:ghi:ACGT+rCAGA", "ACGT-CAGA"),
        ("abc:def:ghi:rACGT+rCAGA", "ACGT-CAGA"),
    ],
)
def test_extract_umi_from_read_name(read_name: str, umi: str) -> None:
    """Test that we can extract UMI from a read name."""
    assert extract_umis_from_read_name(read_name) == umi


@pytest.mark.parametrize(
    "read_name",
    [
        "abc:def:ghi:ArCGT",
        "abc:def:ghi:ACGTr",
        "abc:def:ghi:ACGT-CAGA",
        "abc:def:ghi:ACGT_CAGA",
        "abc:def:ghi:+ACGT",
        "abc:def:ghi:ACGT+",
    ],
)
def test_extract_umi_from_read_name_raises(read_name: str) -> None:
    """Test that we raise an error when the read name includes an invalid UMI
    and strict=True."""
    with pytest.raises(ValueError):
        extract_umis_from_read_name(read_name=read_name, strict=True)


def test_extract_umi_from_read_name_strict_False() -> None:
    """Test that we return None when an invalid UMI is encountered
    and strict=False (but still return a valid UMI)."""
    assert extract_umis_from_read_name(read_name="abc:def:ghi:ArCGT", strict=False) is None
    assert extract_umis_from_read_name(read_name="abc:def:ghi:ACGTr", strict=False) is None
    assert (
        extract_umis_from_read_name(read_name="abc:def:ghi:rACGT+CAGA", strict=False)
        == "ACGT-CAGA"
    )


@pytest.mark.parametrize(
    "read_name, extraction",
    [
        ("abc:def:ghi:jfk:lmn:opq:ACGT", None),  # colons == 6
        ("abc:def:ghi:jfk:lmn:opq:rst:ACGT", "ACGT"),  # colons == 7
    ],
)
def test_strict_extract_umi_from_read_name(read_name: str, extraction: str) -> None:
    """Test that we raise an error when strict=True and number of colons is not 7 or 8."""
    assert extract_umis_from_read_name(read_name, strict=True) == extraction


@pytest.mark.parametrize(
    "read_name",
    [
        ("abc:def:ghi:jfk"),
        ("abc:def:ghi:jfk:lmn:opq:rst:uvw:xyz"),
        ("abc:def:ghi:jfk:lmn:opq:rst:"),  # Invalid UMI
    ],
)
def test_strict_extract_umi_from_read_name_raises(read_name: str) -> None:
    """Test that we raise an error when strict=True and number of colons is not 7 or 8."""
    with pytest.raises(ValueError):
        extract_umis_from_read_name(read_name, strict=True)


@pytest.mark.parametrize("remove_umi, strict", [[True, False], [True, False]])
def test_copy_valid_umi_from_read_name(remove_umi: bool, strict: bool) -> None:
    """Test that we populate the RX field with a valid UMI if remove_umi and strict
    are both True; otherwise do not remove UMI from read.query_name"""
    builder = SamBuilder()
    read = builder.add_single(name="abc:def:ghi:jfk:lmn:opq:rst:GATTACA")
    assert copy_umi_from_read_name(read, strict=strict, remove_umi=remove_umi) is True
    assert read.get_tag("RX") == "GATTACA"
    if remove_umi:
        assert read.query_name == "abc:def:ghi:jfk:lmn:opq:rst"
    else:
        assert read.query_name == "abc:def:ghi:jfk:lmn:opq:rst:GATTACA"
def test_populated_rx_tag() -> None:
    """Test that we raise a ValueError when a record already has a populated RX tag"""
    builder = SamBuilder()
    read = builder.add_single(name="abc:def:ghi:jfk:lmn:opq:rst:GATTACA")
    read.set_tag(tag="RX", value="NNNNACGT")
    assert copy_umi_from_read_name(read, strict=False, remove_umi=True) is False
    assert read.get_tag("RX") == "NNNNACGT"
    assert read.query_name == "abc:def:ghi:jfk:lmn:opq:rst:GATTACA"

def test_copy_invalid_umi_from_read_name() -> None:
    """Test that we do not set the RX tag if we encounter an invalid UMI"""
    builder = SamBuilder()
    read = builder.add_single(name="abc:def:ghi:jfk:lmn:opq:rst:uvw+xyz")
    assert _is_valid_umi(read.query_name) is False
    with pytest.raises(ValueError):
        copy_umi_from_read_name(read, strict=True, remove_umi=True)
    assert read.has_tag("RX") is False
