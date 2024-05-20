import pytest
from fgpyo.sam import extract_umis_from_read_name, _is_valid_umi, copy_umi_from_read_name, AlignedSegment
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
    """Test that we raise an error when the read name includes an invalid UMI."""
    with pytest.raises(ValueError):
        extract_umis_from_read_name(read_name)

@pytest.mark.parametrize(
    "read_name, extraction",
    [
        ("abc:def:ghi:jfk:lmn:opq:ACGT",None), #colons == 6
        ("abc:def:ghi:jfk:lmn:opq:rst:ACGT","ACGT"), #colons == 7
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
        ("abc:def:ghi:jfk:lmn:opq:rst:") #Invalid UMI
    ],
)
def test_strict_extract_umi_from_read_name_raises(read_name: str) -> None:
    """Test that we raise an error when strict=True and number of colons is not 7 or 8."""
    with pytest.raises(ValueError):
        extract_umis_from_read_name(read_name,strict=True)
def test_copy_umi_from_read_name() -> None:
    builder = SamBuilder()
    read = builder.add_single(name="read_name:GATTACA")
    copy_umi_from_read_name(read, remove_umi=False)
    assert read.qname == "read_name:GATTACA"
    assert read.get_tag("RX") == "GATTACA"

def test_copy_remove_umi_from_read_name() -> None:
    builder = SamBuilder()
    read = builder.add_single(name="read_name:GATTACA")
    copy_umi_from_read_name(read, remove_umi=True)
    assert read.qname == "read_name"
    assert read.get_tag("RX") == "GATTACA"