import pytest

from fgpyo.read_structure import ReadSegment
from fgpyo.read_structure import ReadStructure
from fgpyo.read_structure import SegmentType


def _t(off: int, length: int) -> ReadSegment:
    return ReadSegment(offset=off, length=length, kind=SegmentType.Template)


def _b(off: int, length: int) -> ReadSegment:
    return ReadSegment(offset=off, length=length, kind=SegmentType.SampleBarcode)


def _m(off: int, length: int) -> ReadSegment:
    return ReadSegment(offset=off, length=length, kind=SegmentType.MolecularBarcode)


def _c(off: int, length: int) -> ReadSegment:
    return ReadSegment(offset=off, length=length, kind=SegmentType.CellBarcode)


def _s(off: int, length: int) -> ReadSegment:
    return ReadSegment(offset=off, length=length, kind=SegmentType.Skip)


@pytest.mark.parametrize(
    "string,segments",
    [
        ("1T", (_t(0, 1),)),
        ("1B", (_b(0, 1),)),
        ("1M", (_m(0, 1),)),
        ("1S", (_s(0, 1),)),
        ("5C", (_c(0, 5),)),
        ("101T", (_t(0, 101),)),
        (
            "5B101T",
            (
                _b(0, 5),
                _t(5, 101),
            ),
        ),
        ("123456789T", (_t(0, 123456789),)),
        (
            "10T10B10B10S10M",
            (
                _t(0, 10),
                _b(10, 10),
                _b(20, 10),
                _s(30, 10),
                _m(40, 10),
            ),
        ),
    ],
)
def test_read_structure_from_string(string: str, segments: tuple[ReadSegment, ...]) -> None:
    assert ReadStructure.from_string(segments=string).segments == segments


@pytest.mark.parametrize(
    "string,segments",
    [
        (
            "75T 8B 8B 75T",
            (
                _t(0, 75),
                _b(75, 8),
                _b(83, 8),
                _t(91, 75),
            ),
        ),
        (
            " 75T  8B   8B     75T  ",
            (
                _t(0, 75),
                _b(75, 8),
                _b(83, 8),
                _t(91, 75),
            ),
        ),
    ],
)
def test_read_structure_from_string_with_whitespace(
    string: str, segments: tuple[ReadSegment, ...]
) -> None:
    assert ReadStructure.from_string(segments=string).segments == segments


@pytest.mark.parametrize(
    "string,segments",
    [
        ("5M+T", (_m(0, 5), ReadSegment(offset=5, length=None, kind=SegmentType.Template))),
        ("+M", (ReadSegment(offset=0, length=None, kind=SegmentType.MolecularBarcode),)),
    ],
)
def test_read_structure_variable_once_and_only_once_last_segment_ok(
    string: str, segments: tuple[ReadSegment, ...]
) -> None:
    assert ReadStructure.from_string(segments=string).segments == segments


@pytest.mark.parametrize("string", ["+M+T", "+M70T"])
def test_read_structure_rejects_variable_length(string: str) -> None:
    """Variable length should only be permitted in the last segment of the read structure."""
    expected_msg = r"Variable length \(\+\) can only be used in the last segment"
    with pytest.raises(AssertionError, match=expected_msg):
        ReadStructure.from_string(segments=string)


@pytest.mark.parametrize("string", ["++M", "5M70+T", "5M++T"])
def test_read_structure_rejects_unknown_type(string: str) -> None:
    """Segments with unknown type should be rejected."""
    with pytest.raises(ValueError, match="Read structure segment had unknown type"):
        ReadStructure.from_string(segments=string)


@pytest.mark.parametrize(
    "segments,expected",
    [
        ((_t(4092, 1),), (_t(0, 1),)),
        ((_b(4092, 1),), (_b(0, 1),)),
        ((_m(4092, 1),), (_m(0, 1),)),
        ((_s(4092, 1),), (_s(0, 1),)),
        ((_t(4092, 101),), (_t(0, 101),)),
        ((_b(4092, 5), _t(2424, 101)), (_b(0, 5), _t(5, 101))),
        (
            (_t(4092, 101), _b(4092, 101), _b(4092, 101), _s(4092, 101), _m(4092, 101)),
            (_t(0, 101), _b(101, 101), _b(202, 101), _s(303, 101), _m(404, 101)),
        ),
    ],
)
def test_read_structure_from_segments_reset_offset(
    segments: tuple[ReadSegment, ...], expected: tuple[ReadSegment, ...]
) -> None:
    read_structure = ReadStructure.from_segments(segments=segments, reset_offsets=True)
    assert read_structure.segments == expected


@pytest.mark.parametrize("string", ["0T", "9R", "T", "23TT", "23T2", "23T2TT23T"])
def test_read_structure_from_invalid_exception(string: str) -> None:
    with pytest.raises(Exception) as ex:
        assert f"[{string}]" in str(ex)


def test_read_structure_collect_segments_of_a_single_kind() -> None:
    rs: ReadStructure = ReadStructure.from_string("10M9T8B7S10M9T8B7S3C")
    assert rs.template_segments() == (_t(10, 9), _t(44, 9))
    assert rs.molecular_barcode_segments() == (_m(0, 10), _m(34, 10))
    assert rs.sample_barcode_segments() == (_b(19, 8), _b(53, 8))
    assert rs.skip_segments() == (_s(27, 7), _s(61, 7))
    assert rs.cell_barcode_segments() == (_c(68, 3),)


@pytest.mark.parametrize(
    "string,expected", [("75T", "+T"), ("5M70T", "5M+T"), ("+B", "+B"), ("5B+T", "5B+T")]
)
def test_read_structure_with_variable_last_segment(string: str, expected: str) -> None:
    rs = ReadStructure.from_string(string).with_variable_last_segment()
    assert str(rs) == expected


def test_read_structure_extract() -> None:
    rs = ReadStructure.from_string("2T2B2M2S2C")
    extracted = rs.extract("AACCGGTTNN")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "TT" for r in extracted if r.kind == SegmentType.Skip)
    assert all(r.bases == "NN" for r in extracted if r.kind == SegmentType.CellBarcode)

    # too short
    with pytest.raises(AssertionError, match="Read ends before end of segment"):
        rs.extract("AAAAAAA")

    # last segment is truncated
    extracted = rs.with_variable_last_segment().extract("AACCGGTTN")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "TT" for r in extracted if r.kind == SegmentType.Skip)
    assert all(r.bases == "N" for r in extracted if r.kind == SegmentType.CellBarcode)

    # last segment is skipped
    extracted = rs.with_variable_last_segment().extract("AACCGGTT")
    assert all(r.bases == "AA" for r in extracted if r.kind == SegmentType.Template)
    assert all(r.bases == "CC" for r in extracted if r.kind == SegmentType.SampleBarcode)
    assert all(r.bases == "GG" for r in extracted if r.kind == SegmentType.MolecularBarcode)
    assert all(r.bases == "TT" for r in extracted if r.kind == SegmentType.Skip)
    assert all(r.bases == "" for r in extracted if r.kind == SegmentType.CellBarcode)


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
    with pytest.raises(AssertionError, match="Read ends before end of segment"):
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
        ("1T", 0, _t(0, 1)),
        ("1B", 0, _b(0, 1)),
        ("1M", 0, _m(0, 1)),
        ("1S", 0, _s(0, 1)),
        ("101T", 0, _t(0, 101)),
        ("5B101T", 0, _b(0, 5)),
        ("5B101T", 1, _t(5, 101)),
        ("123456789T", 0, _t(0, 123456789)),
        ("10T10B10B10S10M", 0, _t(0, 10)),
        ("10T10B10B10S10M", 1, _b(10, 10)),
        ("10T10B10B10S10M", 2, _b(20, 10)),
        ("10T10B10B10S10M", 3, _s(30, 10)),
        ("10T10B10B10S10M", 4, _m(40, 10)),
    ],
)
def test_read_structure_index(string: str, index: int, segment: ReadSegment) -> None:
    rs = ReadStructure.from_string(string)
    assert rs[index] == segment


def test_segment_type_round_trip() -> None:
    for kind in SegmentType:
        assert str(kind) == kind.value
