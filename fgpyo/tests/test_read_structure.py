from typing import Tuple

import pytest

from fgpyo.read_structure import ReadSegment
from fgpyo.read_structure import ReadStructure
from fgpyo.read_structure import SegmentType


def _T(off: int, len: int) -> ReadSegment:
    return ReadSegment(offset=off, length=len, kind=SegmentType.Template)


def _B(off: int, len: int) -> ReadSegment:
    return ReadSegment(offset=off, length=len, kind=SegmentType.SampleBarcode)


def _M(off: int, len: int) -> ReadSegment:
    return ReadSegment(offset=off, length=len, kind=SegmentType.MolecularBarcode)


def _S(off: int, len: int) -> ReadSegment:
    return ReadSegment(offset=off, length=len, kind=SegmentType.Skip)


@pytest.mark.parametrize(
    "string,segments",
    [
        ("1T", (_T(0, 1),)),
        ("1B", (_B(0, 1),)),
        ("1M", (_M(0, 1),)),
        ("1S", (_S(0, 1),)),
        ("101T", (_T(0, 101),)),
        (
            "5B101T",
            (
                _B(0, 5),
                _T(5, 101),
            ),
        ),
        ("123456789T", (_T(0, 123456789),)),
        (
            "10T10B10B10S10M",
            (
                _T(0, 10),
                _B(10, 10),
                _B(20, 10),
                _S(30, 10),
                _M(40, 10),
            ),
        ),
    ],
)
def test_read_structure_from_string(string: str, segments: Tuple[ReadSegment, ...]) -> None:
    assert ReadStructure.from_string(segments=string).segments == segments


@pytest.mark.parametrize(
    "string,segments",
    [
        (
            "75T 8B 8B 75T",
            (
                _T(0, 75),
                _B(75, 8),
                _B(83, 8),
                _T(91, 75),
            ),
        ),
        (
            " 75T  8B   8B     75T  ",
            (
                _T(0, 75),
                _B(75, 8),
                _B(83, 8),
                _T(91, 75),
            ),
        ),
    ],
)
def test_read_structure_from_string_with_whitespace(
    string: str, segments: Tuple[ReadSegment, ...]
) -> None:
    assert ReadStructure.from_string(segments=string).segments == segments


@pytest.mark.parametrize(
    "string,segments",
    [
        ("5M+T", (_M(0, 5), ReadSegment(offset=5, length=None, kind=SegmentType.Template))),
        ("+M", (ReadSegment(offset=0, length=None, kind=SegmentType.MolecularBarcode),)),
    ],
)
def test_read_structure_variable_once_and_only_once_last_segment_ok(
    string: str, segments: Tuple[ReadSegment, ...]
) -> None:
    assert ReadStructure.from_string(segments=string).segments == segments


@pytest.mark.parametrize(
    "string",
    ["++M", "5M++T", "5M70+T", "+M+T", "+M70T"],
)
def test_read_structure_variable_once_and_only_once_last_segment_exception(string: str) -> None:
    with pytest.raises(Exception):
        ReadStructure.from_string(segments=string)


@pytest.mark.parametrize(
    "segments,expected",
    [
        ((_T(4092, 1),), (_T(0, 1),)),
        ((_B(4092, 1),), (_B(0, 1),)),
        ((_M(4092, 1),), (_M(0, 1),)),
        ((_S(4092, 1),), (_S(0, 1),)),
        ((_T(4092, 101),), (_T(0, 101),)),
        ((_B(4092, 5), _T(2424, 101)), (_B(0, 5), _T(5, 101))),
        (
            (_T(4092, 101), _B(4092, 101), _B(4092, 101), _S(4092, 101), _M(4092, 101)),
            (_T(0, 101), _B(101, 101), _B(202, 101), _S(303, 101), _M(404, 101)),
        ),
    ],
)
def test_read_structure_from_segments_reset_offset(
    segments: Tuple[ReadSegment, ...], expected: Tuple[ReadSegment, ...]
) -> None:

    read_structure = ReadStructure.from_segments(segments=segments, reset_offsets=True)
    assert read_structure.segments == expected


@pytest.mark.parametrize("string", ["0T", "9R", "T", "23TT", "23T2", "23T2TT23T"])
def test_read_structure_from_invalid_exception(string: str) -> None:
    with pytest.raises(Exception) as ex:
        assert f"[{string}]" in str(ex)


def test_read_structure_collect_segments_of_a_single_kind() -> None:
    rs: ReadStructure = ReadStructure.from_string("10M9T8B7S10M9T8B7S")
    assert rs.template_segments() == (_T(10, 9), _T(44, 9))
    assert rs.molecular_barcode_segments() == (_M(0, 10), _M(34, 10))
    assert rs.sample_barcode_segments() == (_B(19, 8), _B(53, 8))
    assert rs.skip_segments() == (_S(27, 7), _S(61, 7))


@pytest.mark.parametrize(
    "string,expected", [("75T", "+T"), ("5M70T", "5M+T"), ("+B", "+B"), ("5B+T", "5B+T")]
)
def test_read_structure_with_variable_last_segment(string: str, expected: str) -> None:
    rs = ReadStructure.from_string(string).with_variable_last_segment()
    assert str(rs) == expected


def test_read_structure_extract() -> None:
    rs = ReadStructure.from_string("2T2B2M2S")
    extracted = rs.extract("AACCGGTT")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "TT" for r in extracted if r.kind == SegmentType.Skip)

    # too short
    with pytest.raises(Exception):
        rs.extract("AAAAAAA")

    # last segment is truncated
    extracted = rs.with_variable_last_segment().extract("AACCGGT")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "T" for r in extracted if r.kind == SegmentType.Skip)

    # last segment is skipped
    extracted = rs.with_variable_last_segment().extract("AACCGG")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "" for r in extracted if r.kind == SegmentType.Skip)


def test_read_structure_extract_with_quals() -> None:
    rs = ReadStructure.from_string("2T2B2M2S")
    extracted = rs.extract_with_quals("AACCGGTT", "11223344")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.quals == "11" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.quals == "22" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.quals == "33" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "TT" for r in extracted if r.kind == SegmentType.Skip)
    assert all(r.quals == "44" for r in extracted if r.kind == SegmentType.Skip)

    # too short
    with pytest.raises(Exception):
        rs.extract_with_quals("AAAAAAA", "1122334")

    # last segment is truncated
    extracted = rs.with_variable_last_segment().extract_with_quals("AACCGGT", "1122334")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.quals == "11" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.quals == "22" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.quals == "33" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "T" for r in extracted if r.kind == SegmentType.Skip)
    assert all(r.quals == "4" for r in extracted if r.kind == SegmentType.Skip)

    # last segment is skipped
    extracted = rs.with_variable_last_segment().extract_with_quals("AACCGG", "112233")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.quals == "11" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.quals == "22" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.quals == "33" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "" for r in extracted if r.kind == SegmentType.Skip)
    assert all(r.quals == "" for r in extracted if r.kind == SegmentType.Skip)


@pytest.mark.parametrize(
    "string,length",
    [
        ("1T", 1),
        ("1B", 1),
        ("1M", 1),
        ("1S", 1),
        ("101T", 1),
        ("5B101T", 2),
        ("123456789T", 1),
        ("10T10B10B10S10M", 5),
    ],
)
def test_read_structure_length(string: str, length: int) -> None:
    rs = ReadStructure.from_string(string)
    assert rs.length == length
    assert len(rs) == length


@pytest.mark.parametrize(
    "string,index,segment",
    [
        ("1T", 0, _T(0, 1)),
        ("1B", 0, _B(0, 1)),
        ("1M", 0, _M(0, 1)),
        ("1S", 0, _S(0, 1)),
        ("101T", 0, _T(0, 101)),
        ("5B101T", 0, _B(0, 5)),
        ("5B101T", 1, _T(5, 101)),
        ("123456789T", 0, _T(0, 123456789)),
        ("10T10B10B10S10M", 0, _T(0, 10)),
        ("10T10B10B10S10M", 1, _B(10, 10)),
        ("10T10B10B10S10M", 2, _B(20, 10)),
        ("10T10B10B10S10M", 3, _S(30, 10)),
        ("10T10B10B10S10M", 4, _M(40, 10)),
    ],
)
def test_read_structure_index(string: str, index: int, segment: ReadSegment) -> None:
    rs = ReadStructure.from_string(string)
    assert rs[index] == segment


def test_segment_type_round_trip() -> None:
    for kind in SegmentType:
        assert str(kind) == kind.value
