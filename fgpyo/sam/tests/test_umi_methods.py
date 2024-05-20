import pytest
from fgpyo.sam import extract_umi_from_read_name, _is_valid_umi

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
    assert extract_umi_from_read_name(read_name) == umi


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
        extract_umi_from_read_name(read_name)