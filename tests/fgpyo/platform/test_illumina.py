"""Basic tests for Illumina-specific UMI Methods"""

from typing import Optional

import pytest

from fgpyo.platform.illumina import _is_valid_umi
from fgpyo.platform.illumina import copy_umi_from_read_name
from fgpyo.platform.illumina import extract_umis_from_read_name
from fgpyo.sam.builder import SamBuilder


@pytest.mark.parametrize(
    "umi, validity",
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
    "read_name, expected_umi",
    [
        ("abc:ACGT", "ACGT"),
        ("abc:def:ghi:ACGT", "ACGT"),
        ("abc:def:ghi:rACGT", "ACGT"),
        ("abc:def:ghi:rACGT+CAGA", "ACGT-CAGA"),
        ("abc:def:ghi:ACGT+rCAGA", "ACGT-CAGA"),
        ("abc:def:ghi:rACGT+rCAGA", "ACGT-CAGA"),
    ],
)
def test_extract_umi_from_read_name(read_name: str, expected_umi: str) -> None:
    """Test that we can extract UMIs from a read name."""
    assert extract_umis_from_read_name(read_name) == expected_umi


@pytest.mark.parametrize(
    "read_name",
    [  # too few colon-delimited fields
        "abc:def:ghi:ArCGT",
        "abc:def:ghi:ACGTr",
        "abc:def:ghi:ACGT-CAGA",
        "abc:def:ghi:ACGT_CAGA",
        "abc:def:ghi:+ACGT",
        "abc:def:ghi:ACGT+",
    ],
)
def test_extract_umi_malformed_raises(read_name: str) -> None:
    """Test that we raise an error when the number of colon-delimited fields is < 7
    when strict is True."""
    with pytest.raises(ValueError, match="Trying to extract UMIs from read with"):
        extract_umis_from_read_name(read_name=read_name, strict=True)


@pytest.mark.parametrize(
    "read_name",  # expected number of fields but invalid UMIs
    [
        "abc:def:ghi:jkl:mno:qrs:tuv:wxy",
        "abc:def:ghi:jkl:mno:qrs:tuv:ACGT_CAGA",
        "abc:def:ghi:jkl:mno:qrs:tuv:ACGT-CAGA",
        "abc:def:ghi:jkl:mno:qrs:tuv:ACGTr",
        "abc:def:ghi:jfk:lmn:opq:rst:",
    ],
)
def test_extract_invalid_umi_raises(read_name: str) -> None:
    """Test that we raise an error when the read name includes an invalid UMI
    and strict is True."""
    with pytest.raises(ValueError, match="Invalid UMIs found in read name"):
        extract_umis_from_read_name(read_name=read_name, strict=True)


@pytest.mark.parametrize(
    "read_name, expected_umi",
    [
        ("abc:def:ghi:ArCGT", None),
        ("abc:def:ghi:ACGTr", None),
        ("abc:def:ghi:ACGT-CAGA", None),
        ("abc:def:ghi:ACGT_CAGA", None),
        ("abc:def:ghi:+ACGT", None),
        ("abc:def:ghi:ACGT+", None),
        ("abc:def:ghi:rACGT+CAGA", "ACGT-CAGA"),
    ],
)
def test_extract_umi_from_read_name_strict_false(
    read_name: str, expected_umi: Optional[str]
) -> None:
    """Test that we return None when an invalid UMI is encountered
    and strict is False. Otherwise, return a valid UMI."""
    assert extract_umis_from_read_name(read_name=read_name, strict=False) == expected_umi


@pytest.mark.parametrize(
    "read_name, extraction",
    [
        ("abc:def:ghi:jfk:lmn:opq:ACGT", None),  # colons == 6
        ("abc:def:ghi:jfk:lmn:opq:rst:ACGT", "ACGT"),  # colons == 7
        (
            "abc:def:ghi:jfk:lmn:opq:rst+uvw:ACGT",
            "ACGT",
        ),  # colons == 7, penultimate multi-UMI
        (
            "abc:def:ghi:jfk:lmn:opq:rst:AGT+CAT",
            "AGT-CAT",
        ),  # last field (multi-UMI) is returned
    ],
)
def test_strict_extract_umi_from_read_name(read_name: str, extraction: str) -> None:
    """Test that we extract UMI from read name as expected when strict is True."""
    assert extract_umis_from_read_name(read_name, strict=True) == extraction


@pytest.mark.parametrize("remove_umi, strict", [[True, False], [True, False]])
def test_copy_valid_umi_from_read_name(remove_umi: bool, strict: bool) -> None:
    """Test that we populate the RX field with a valid UMI if remove_umi and strict
    are both True; otherwise do not remove UMI from read.query_name."""
    builder = SamBuilder()
    read = builder.add_single(name="abc:def:ghi:jfk:lmn:opq:rst:GATTACA")
    assert copy_umi_from_read_name(read, strict=strict, remove_umi=remove_umi) is True
    assert read.get_tag("RX") == "GATTACA"
    if remove_umi:
        assert read.query_name == "abc:def:ghi:jfk:lmn:opq:rst"
    else:
        assert read.query_name == "abc:def:ghi:jfk:lmn:opq:rst:GATTACA"


def test_populated_rx_tag_raises() -> None:
    """Test that we raise a ValueError when a record already has a populated RX tag."""
    builder = SamBuilder()
    read = builder.add_single(name="abc:def:ghi:jfk:lmn:opq:rst:GATTACA")
    read.set_tag(tag="RX", value="NNNNACGT")
    with pytest.raises(
        ValueError, match=f"Record {read.query_name} already has a populated RX tag"
    ):
        copy_umi_from_read_name(read, strict=False, remove_umi=True)
    assert read.get_tag("RX") == "NNNNACGT"
    assert read.query_name == "abc:def:ghi:jfk:lmn:opq:rst:GATTACA"


def test_copy_invalid_umi_from_read_name_raises() -> None:
    """Test that with an invalid UMI, we raise an error and do not set the RX tag
    when strict is True."""
    builder = SamBuilder()
    read = builder.add_single(name="abc:def:ghi:jfk:lmn:opq:rst:uvw+xyz")
    assert _is_valid_umi(read.query_name) is False
    with pytest.raises(ValueError, match="Invalid UMIs found in read name:"):
        copy_umi_from_read_name(read, strict=True, remove_umi=True)
    assert read.has_tag("RX") is False
