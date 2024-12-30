"""Tests for :py:mod:`~fgpyo.sam`"""

from pathlib import Path
from tempfile import NamedTemporaryFile as NamedTemp
from typing import Any
from typing import Generator
from typing import List
from typing import Tuple
from typing import Union

import pysam
import pytest
from pysam import AlignmentHeader

import fgpyo.sam as sam
from fgpyo.sam import Cigar
from fgpyo.sam import CigarElement
from fgpyo.sam import CigarOp
from fgpyo.sam import CigarParsingException
from fgpyo.sam import PairOrientation
from fgpyo.sam import SamFileType
from fgpyo.sam import is_proper_pair
from fgpyo.sam import set_mate_info
from fgpyo.sam import set_mate_info_on_secondary
from fgpyo.sam import set_mate_info_on_supplementary
from fgpyo.sam import set_pair_info
from fgpyo.sam import sum_of_base_qualities
from fgpyo.sam.builder import SamBuilder


@pytest.mark.parametrize("file_type", list(SamFileType))
@pytest.mark.parametrize("as_str", [True, False])
def test_sam_file_type_from_path(file_type: SamFileType, as_str: bool) -> None:
    path: Union[Path, str]
    if as_str:
        path = "/path/to/some/file" + file_type.extension
    else:
        path = Path("/path/to/some/file" + file_type.extension)
    assert SamFileType.from_path(path=path) == file_type


def test_sam_file_type_invalid_path() -> None:
    path = "/path/to/excel.xls"
    with pytest.raises(ValueError) as ex:
        SamFileType.from_path(path=path)
    assert "Could not infer file type from " + path in str(ex)


@pytest.fixture
def valid_sam() -> Path:
    return Path(__file__).parent / "data" / "valid.sam"


@pytest.fixture
def valid_bam(valid_sam: Path) -> Generator[Path, None, None]:
    bam: Path = Path(__file__).parent / "data" / "valid.bam"
    num_read = 0
    with sam.reader(valid_sam) as fh_in:
        with sam.writer(bam, fh_in.header, file_type=SamFileType.BAM) as fh_out:
            for rec in fh_in:
                num_read += 1
                fh_out.write(rec)
    assert num_read == 8
    yield bam
    bam.unlink()


@pytest.fixture
def unmapped_sam() -> Path:
    return Path(__file__).parent / "data" / "unmapped.sam"


@pytest.fixture(scope="function")
def in_path(request: Any, valid_sam: Path, valid_bam: Path) -> Path:
    """A fixture for test_sam_file_open_reading to modify in_path prior to executing.

    Returns:
         the path corresponding to the given file type (i.e. SAM or BAM).
    """
    file_type = request.param
    return valid_sam if file_type == SamFileType.SAM else valid_bam


@pytest.mark.parametrize(
    "in_path,file_type",
    [(SamFileType.SAM, SamFileType.SAM), (SamFileType.BAM, SamFileType.BAM)],
    indirect=["in_path"],
)  # Note: This modifies in_path via the in_path fixture
def test_sam_file_open_reading(in_path: Path, file_type: SamFileType) -> None:
    # file pointer
    with in_path.open(mode="rb") as fp:
        with sam._pysam_open(path=fp, open_for_reading=True, file_type=file_type) as samfile:
            assert sum(1 for _ in samfile) == 8

    # Path
    with sam._pysam_open(path=in_path, open_for_reading=True, file_type=file_type) as samfile:
        assert sum(1 for _ in samfile) == 8

    # str
    str_path = str(in_path)
    with sam._pysam_open(path=str_path, open_for_reading=True, file_type=file_type) as samfile:
        assert sum(1 for _ in samfile) == 8


def test_sam_file_open_reading_autorecognize(valid_sam: Path) -> None:
    with sam._pysam_open(path=valid_sam, open_for_reading=True, file_type=None) as samfile:
        assert sum(1 for _ in samfile) == 8


def test_sam_file_open_reading_with_reader(valid_sam: Path) -> None:
    with sam.reader(path=valid_sam, file_type=None) as samfile:
        assert sum(1 for _ in samfile) == 8


def test_unmapped_sam_file_open_reading_with_reader(unmapped_sam: Path) -> None:
    with sam.reader(path=unmapped_sam, unmapped=True) as samfile:
        assert len([read for read in samfile.fetch() if read.is_unmapped]) == 1


@pytest.fixture
def expected_records(valid_sam: Path) -> List[pysam.AlignedSegment]:
    """Returns the records that are found in the valid_sam."""
    with sam.reader(valid_sam) as fh:
        return [r for r in fh]


@pytest.fixture
def header_dict(valid_sam: Path) -> AlignmentHeader:
    """Returns the multi-level dictionary in the valid_sam."""
    with sam.reader(valid_sam) as fh:
        return fh.header


def assert_actual_vs_expected(
    actual_path: str, expected_records: List[pysam.AlignedSegment]
) -> None:
    """Helper method to ensure the expected records are in the SAM/BAM at the actual path."""
    with sam.reader(actual_path) as sam_reader:
        actual_records = [r for r in sam_reader]
    for actual, expected in zip(actual_records, expected_records):
        assert actual == expected
    assert len(actual_records) == len(expected_records)


@pytest.mark.parametrize("file_type", [SamFileType.SAM, SamFileType.BAM])
def test_sam_file_open_writing(
    file_type: SamFileType,
    expected_records: List[pysam.AlignedSegment],
    header_dict: AlignmentHeader,
    tmp_path: Path,
) -> None:
    # use header as a keyword argument
    with NamedTemp(suffix=file_type.extension, dir=tmp_path, mode="w", delete=False) as fp:
        kwargs = {"header": header_dict}
        with sam._pysam_open(
            path=fp.file,
            open_for_reading=False,
            file_type=file_type,
            **kwargs,  # type: ignore[arg-type]
        ) as sam_writer:
            for r in expected_records:
                sam_writer.write(r)
    assert_actual_vs_expected(fp.name, expected_records)


def test_sam_file_open_writing_header_keyword(
    expected_records: List[pysam.AlignedSegment],
    header_dict: AlignmentHeader,
    tmp_path: Path,
) -> None:
    # Use SamWriter
    # use header as a keyword argument
    with NamedTemp(suffix=".sam", dir=tmp_path, mode="w", delete=False) as fp:
        with sam.writer(path=fp.name, header=header_dict, file_type=SamFileType.SAM) as sam_writer:
            for r in expected_records:
                sam_writer.write(r)
    assert_actual_vs_expected(fp.name, expected_records)


def test_cigar_op_util_from_character() -> None:
    operators = [operator for operator in CigarOp]
    characters = [operator.character for operator in operators]
    for i, character in enumerate(characters):
        assert CigarOp.from_character(character) == operators[i]


def test_cigar_op_util_from_code() -> None:
    operators = [operator for operator in CigarOp]
    codes = [operator.code for operator in operators]
    for i, code in enumerate(codes):
        assert CigarOp.from_code(code) == operators[i]


@pytest.mark.parametrize(
    "character,operator_length,length_on_query,length_on_target",
    [("M", 10, 10, 10), ("I", 10, 10, 0), ("D", 10, 0, 10), ("S", 10, 10, 0)],
)
def test_cigar_element_length_on(
    character: str, operator_length: int, length_on_query: int, length_on_target: int
) -> None:
    operator = CigarOp.from_character(character)
    element = CigarElement(operator_length, operator)
    assert element.length == operator_length
    assert element.length_on_query == length_on_query
    assert element.length_on_target == length_on_target


@pytest.mark.parametrize("character", ["M", "I", "D", "S"])
def test_invalid_cigar_element(character: str) -> None:
    with pytest.raises(ValueError):
        CigarElement(-1, operator=CigarOp.from_character(character))


@pytest.mark.parametrize(
    "cigartuples,cigarstring",
    [
        ([], "*"),  # Empty cigar
        ([(0, 10), (1, 5), (0, 1)], "10M5I1M"),  # A simple example
        ([(0, 10), (1, 5), (1, 5)], "10M5I5I"),  # do not join adjacent operators of the same type
        ([(op.code, op.code + 1) for op in CigarOp], "1M2I3D4N5S6H7P8=9X"),  # all operators
    ],
)
def test_cigar_from_cigartuples(cigartuples: List[Tuple[int, int]], cigarstring: str) -> None:
    cigar = Cigar.from_cigartuples(cigartuples)
    assert str(cigar) == cigarstring


def test_cigar_from_cigartuples_malformed() -> None:
    with pytest.raises(CigarParsingException, match=r".*Malformed cigar tuples.*"):
        cigartuples = [(0, 10), (1, 5), (22, 1)]
        Cigar.from_cigartuples(cigartuples)


def test_pretty_cigarstring_exception() -> None:
    cigar = "10M5U4M"
    index = 4
    expected = "10M5[U]4M"
    with pytest.raises(CigarParsingException, match=r".*Malformed cigar") as ex:
        raise Cigar._pretty_cigarstring_exception(cigar, index)

    # Known issue, `mypy` thinks the `raise` above makes the following unreachable
    # https://github.com/python/mypy/issues/8985
    # https://github.com/python/mypy/issues/8766
    assert expected in str(ex)  # type: ignore[unreachable]

    expected = cigar + "[]"
    with pytest.raises(CigarParsingException, match=r".*Malformed cigar") as ex:
        raise Cigar._pretty_cigarstring_exception(cigar, len(cigar))
    assert expected in str(ex)


def test_from_cigarstring() -> None:
    # Empty cigar
    assert str(Cigar.from_cigarstring("*")) == "*"

    elements = []
    for i, operator in enumerate(CigarOp):
        elements.append(CigarElement(i + 1, operator))
    cigarstring = str(Cigar(tuple(elements)))
    assert str(Cigar.from_cigarstring(cigarstring)) == cigarstring


def test_from_cigarstring_op_should_start_with_digit() -> None:
    cigars = ["", "M", "10MI", "10M5SU"]
    errors = ["", "[M]", "10M[I]", "10M5S[U]"]
    for cigar, error in zip(cigars, errors):
        match = "Malformed cigar: " + error if cigar else "Cigar string was empty"
        with pytest.raises(CigarParsingException) as ex:
            Cigar.from_cigarstring(cigar)
        assert match in str(ex)


def test_from_cigarstring_no_length() -> None:
    cigars = ["M", "10MS"]
    errors = ["", "10M[S]"]
    for cigar, error in zip(cigars, errors):
        with pytest.raises(CigarParsingException) as ex:
            Cigar.from_cigarstring(cigar)
        assert "Malformed cigar: " + error in str(ex)


def test_from_cigarstring_invalid_operator() -> None:
    cigars = ["10U", "10M5U"]
    errors = ["10[U]", "10M5[U]"]
    for cigar, error in zip(cigars, errors):
        with pytest.raises(CigarParsingException) as ex:
            Cigar.from_cigarstring(cigar)
        assert "Malformed cigar: " + error in str(ex)


def test_from_cigarstring_missing_operator() -> None:
    cigars = ["10", "10M5"]
    errors = ["10[]", "10M5[]"]
    for cigar, error in zip(cigars, errors):
        with pytest.raises(CigarParsingException) as ex:
            Cigar.from_cigarstring(cigar)
        assert "Malformed cigar: " + error in str(ex)


def test_is_indel() -> None:
    indels = [op for op in CigarOp if op.is_indel]
    assert indels == [CigarOp.I, CigarOp.D]


def test_is_clipping() -> None:
    clips = [op for op in CigarOp if op.is_clipping]
    assert clips == [CigarOp.S, CigarOp.H]


def test_pair_orientation_build_with_r2() -> None:
    """Test that we can build all pair orientations with R1 and R2."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    assert PairOrientation.from_recs(r1, r2) is PairOrientation.FR
    assert PairOrientation.from_recs(r1) is PairOrientation.FR
    assert PairOrientation.from_recs(r2) is PairOrientation.FR

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = False
    r2.is_forward = True
    sam.set_mate_info(r1, r2)
    assert PairOrientation.from_recs(r1, r2) is PairOrientation.RF
    assert PairOrientation.from_recs(r1) is PairOrientation.RF
    assert PairOrientation.from_recs(r2) is PairOrientation.RF

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = True
    r2.is_forward = True

    sam.set_mate_info(r1, r2)
    assert PairOrientation.from_recs(r1, r2) is PairOrientation.TANDEM
    assert PairOrientation.from_recs(r1) is PairOrientation.TANDEM
    assert PairOrientation.from_recs(r2) is PairOrientation.TANDEM

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = False
    r2.is_forward = False

    sam.set_mate_info(r1, r2)
    assert PairOrientation.from_recs(r1, r2) is PairOrientation.TANDEM
    assert PairOrientation.from_recs(r1) is PairOrientation.TANDEM
    assert PairOrientation.from_recs(r2) is PairOrientation.TANDEM


def test_pair_orientation_is_fr_if_opposite_directions_and_overlapping() -> None:
    """Test the pair orientation is always FR if the reads overlap and are oriented opposite."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="10M", start2=100, cigar2="10M")
    assert PairOrientation.from_recs(r1, r2) is PairOrientation.FR
    assert PairOrientation.from_recs(r1) is PairOrientation.FR
    assert PairOrientation.from_recs(r2) is PairOrientation.FR

    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="10M", start2=100, cigar2="10M")
    r1.is_reverse = True
    r2.is_reverse = False

    sam.set_mate_info(r1, r2)
    assert PairOrientation.from_recs(r1, r2) is PairOrientation.FR
    assert PairOrientation.from_recs(r1) is PairOrientation.FR
    assert PairOrientation.from_recs(r2) is PairOrientation.FR


def test_a_single_bp_alignment_at_end_of_rec_one_is_still_fr_orientations() -> None:
    """Test a single bp alignment at the end of a mate's alignment is still FR based on rec1."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=5, cigar1="5M", start2=5, cigar2="1M")
    assert PairOrientation.from_recs(r1, r2) is PairOrientation.FR
    assert PairOrientation.from_recs(r1) is PairOrientation.FR
    assert PairOrientation.from_recs(r2) is PairOrientation.FR


def test_pair_orientation_build_with_either_unmapped() -> None:
    """Test that we can return None with either R1 and R2 unmapped (or both)."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair()
    assert r1.is_unmapped
    assert r2.is_unmapped
    assert PairOrientation.from_recs(r1, r2) is None
    assert PairOrientation.from_recs(r1) is None
    assert PairOrientation.from_recs(r2) is None

    r1, r2 = builder.add_pair(chrom="chr1", start1=100)
    assert r1.is_mapped
    assert r2.is_unmapped
    assert PairOrientation.from_recs(r1, r2) is None
    assert PairOrientation.from_recs(r1) is None
    assert PairOrientation.from_recs(r2) is None

    r1, r2 = builder.add_pair(chrom="chr1", start2=100)
    assert r1.is_unmapped
    assert r2.is_mapped
    assert PairOrientation.from_recs(r1, r2) is None
    assert PairOrientation.from_recs(r1) is None
    assert PairOrientation.from_recs(r2) is None


def test_pair_orientation_build_with_no_r2_but_r2_mapped() -> None:
    """Test that we can build all pair orientations with R1 and no R2, but R2 is mapped."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    assert PairOrientation.from_recs(r1) is PairOrientation.FR

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = False
    r2.is_forward = True
    sam.set_mate_info(r1, r2)
    assert PairOrientation.from_recs(r1) is PairOrientation.RF

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = True
    r2.is_forward = True
    sam.set_mate_info(r1, r2)
    assert PairOrientation.from_recs(r1) is PairOrientation.TANDEM

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = False
    r2.is_forward = False
    sam.set_mate_info(r1, r2)
    assert PairOrientation.from_recs(r1) is PairOrientation.TANDEM


def test_pair_orientation_build_with_either_unmapped_but_no_r2() -> None:
    """Test that we can return None with either R1 and R2 unmapped (or both), but no R2."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair()
    assert r1.is_unmapped
    assert r2.is_unmapped
    assert PairOrientation.from_recs(r1) is None

    r1, r2 = builder.add_pair(chrom="chr1", start1=100)
    assert r1.is_mapped
    assert r2.is_unmapped
    assert PairOrientation.from_recs(r1) is None

    r1, r2 = builder.add_pair(chrom="chr1", start2=100)
    assert r1.is_unmapped
    assert r2.is_mapped
    assert PairOrientation.from_recs(r1) is None


def test_pair_orientation_build_raises_if_it_cant_find_mate_cigar_tag_positive_fr() -> None:
    """Test that an exception is raised if we cannot find the mate cigar tag."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=16, cigar1="10M", start2=15, cigar2="10M")
    r1.set_tag("MC", None)  # Clear out the MC tag.
    r2.set_tag("MC", None)  # Clear out the MC tag.

    assert PairOrientation.from_recs(r1, r2) is PairOrientation.FR

    with pytest.raises(ValueError):
        PairOrientation.from_recs(r1)

    assert PairOrientation.from_recs(r2) is PairOrientation.FR


def test_pair_orientation_build_raises_if_it_cant_find_mate_cigar_tag_positive_rf() -> None:
    """Test that an exception is raised if we cannot find the mate cigar tag."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=16, cigar1="1M", start2=15, cigar2="1M")
    sam.set_mate_info(r1, r2)

    assert PairOrientation.from_recs(r1, r2) is PairOrientation.RF

    r1.set_tag("MC", None)  # Clear out the MC tag.
    r2.set_tag("MC", None)  # Clear out the MC tag.

    with pytest.raises(ValueError):
        PairOrientation.from_recs(r1)

    assert PairOrientation.from_recs(r2) is PairOrientation.RF


def test_is_proper_pair_when_actually_proper() -> None:
    """Test that is_proper_pair returns True when reads are properly paired."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    assert is_proper_pair(r1, r2)

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="10M", start2=100, cigar2="10M")
    r1.is_reverse = True
    r2.is_reverse = False
    sam.set_mate_info(r1, r2)
    assert is_proper_pair(r1, r2)


def test_is_proper_pair_when_actually_proper_and_no_r2() -> None:
    """Test that is_proper_pair returns True when reads are properly paired, but no R2."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    assert is_proper_pair(r1)

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="10M", start2=100, cigar2="10M")
    r1.is_reverse = True
    r2.is_reverse = False
    sam.set_mate_info(r1, r2)
    assert is_proper_pair(r1)


def test_not_is_proper_pair_if_wrong_orientation() -> None:
    """Test that reads are not properly paired if they are not in the right orientation."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = False
    r2.is_forward = True
    sam.set_mate_info(r1, r2)
    assert not is_proper_pair(r1, r2)

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = True
    r2.is_forward = True
    sam.set_mate_info(r1, r2)
    assert not is_proper_pair(r1, r2)

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = False
    r2.is_forward = False
    sam.set_mate_info(r1, r2)
    assert not is_proper_pair(r1, r2)


def test_not_is_proper_pair_if_wrong_orientation_and_no_r2() -> None:
    """Test reads are not properly paired if they are not in the right orientation, but no R2."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = False
    r2.is_forward = True
    sam.set_mate_info(r1, r2)
    assert not is_proper_pair(r1)

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = True
    r2.is_forward = True
    sam.set_mate_info(r1, r2)
    assert not is_proper_pair(r1)

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    r1.is_forward = False
    r2.is_forward = False
    sam.set_mate_info(r1, r2)
    assert not is_proper_pair(r1)


def test_not_is_proper_pair_if_too_far_apart() -> None:
    """Test that reads are not properly paired if they are too far apart."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, start2=100 + 1000)
    assert not is_proper_pair(r1, r2)


def test_is_not_proper_pair_with_custom_isize_func() -> None:
    """Test that reads are not properly paired because of a custom isize function."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, start2=100)
    assert is_proper_pair(r1, r2)
    assert not is_proper_pair(r1, r2, isize=lambda a, b: False)


def test_isize_when_r2_defined() -> None:
    """Tests that an insert size can be calculated when both input records are defined."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    assert sam.isize(r1, r2) == 190
    assert sam.isize(r2, r1) == -190

    r2.is_unmapped = True
    assert sam.isize(r1, r2) == 0


def test_isize_when_r2_undefined() -> None:
    """Tests that an insert size can be calculated when R1 is provided only."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")
    assert sam.isize(r1) == 190
    assert sam.isize(r2) == -190

    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M")
    assert sam.isize(r1) == 0
    assert sam.isize(r2) == 0


def test_isize_when_r2_undefined_indels_in_r2_cigar() -> None:
    """Tests that an insert size can be derived without R2 by using R2's cigar."""
    builder = SamBuilder()
    r1, _ = builder.add_pair(
        chrom="chr1",
        start1=100,
        cigar1="115M",
        start2=250,
        cigar2="10S5M1D1M1D2I2D30M",  # only 40bp reference-consuming operators
    )
    assert sam.isize(r1) == 190


def test_isize_raises_when_r2_not_provided_and_mate_cigar_tag_unset_r1() -> None:
    """Tests an exception is raised when the mate cigar tag is not on rec1 and rec2 is missing."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=100, cigar1="115M", start2=250, cigar2="40M")

    r1.set_tag("MC", None)

    assert sam.isize(r2) == -190

    with pytest.raises(
        ValueError, match="Cannot determine proper pair status without a mate cigar"
    ):
        sam.isize(r1)


def test_sum_of_base_qualities() -> None:
    builder = SamBuilder(r1_len=5, r2_len=5)
    single = builder.add_single(quals=[1, 2, 3, 4, 5])
    assert sum_of_base_qualities(single, min_quality_score=0) == 15


def test_sum_of_base_qualities_some_below_minimum() -> None:
    builder = SamBuilder(r1_len=5, r2_len=5)
    single = builder.add_single(quals=[1, 2, 3, 4, 5])
    assert sum_of_base_qualities(single, min_quality_score=4) == 9


def test_calc_edit_info_no_edits() -> None:
    chrom = "ACGCTAGACTGCTAGCAGCATCTCATAGCACTTCGCGCTATAGCGATATAAATATCGCGATCTAGCG"
    builder = SamBuilder(r1_len=30)
    rec = builder.add_single(bases=chrom[10:40], chrom="chr1", start=10, cigar="30M")
    info = sam.calculate_edit_info(rec, chrom)
    assert info.mismatches == 0
    assert info.nm == 0


def test_calc_edit_info_no_edits_with_offset() -> None:
    chrom = "ACGCTAGACTGCTAGCAGCATCTCATAGCACTTCGCGCTATAGCGATATAAATATCGCGATCTAGCG"
    builder = SamBuilder(r1_len=30)
    rec = builder.add_single(bases=chrom[10:40], chrom="chr1", start=10, cigar="30M")
    info = sam.calculate_edit_info(rec, chrom[10:40], reference_offset=0)
    assert info.mismatches == 0
    assert info.nm == 0


def test_calc_edit_info_with_mms_and_insertions() -> None:
    chrom = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    builder = SamBuilder(r1_len=30)
    rec = builder.add_single(
        bases="AAAAACAAAAAAAAGGGAAAAAAAAAAAAA", chrom="chr1", start=10, cigar="14M3I13M"
    )

    info = sam.calculate_edit_info(rec, chrom)
    assert info.mismatches == 1
    assert info.insertions == 1
    assert info.inserted_bases == 3
    assert info.deletions == 0
    assert info.deleted_bases == 0
    assert info.nm == 4


def test_calc_edit_info_with_clipping_and_deletions() -> None:
    chrom = "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"
    builder = SamBuilder(r1_len=30)
    rec = builder.add_single(
        bases="NNNNACGTGTACGTACGTACGTACGTACGT", chrom="chr1", start=8, cigar="4S4M2D22M"
    )

    info = sam.calculate_edit_info(rec, chrom)
    assert info.mismatches == 0
    assert info.insertions == 0
    assert info.inserted_bases == 0
    assert info.deletions == 1
    assert info.deleted_bases == 2
    assert info.nm == 2


def test_calc_edit_info_with_aligned_Ns() -> None:
    """Ns in query match Ns in reference, but should be counted as mismatches for NM."""
    chrom = "ACGTNCGTACNTACGTACGTANNNACGTACACGTACGTACGTACGTACGTACGTACGTAT"
    builder = SamBuilder(r1_len=30)
    rec = builder.add_single(
        bases="ACGTNCGTACNTACGTACGTANNNACGTAC", chrom="chr1", start=0, cigar="30M"
    )

    info = sam.calculate_edit_info(rec, chrom)
    assert info.mismatches == 5
    assert info.insertions == 0
    assert info.inserted_bases == 0
    assert info.deletions == 0
    assert info.deleted_bases == 0
    assert info.nm == 5


def test_set_mate_info_raises_not_opposite_read_ordinals() -> None:
    """Test set_mate_info raises an exception for mismatched read ordinals."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="x", read_num=1)
    with pytest.raises(
        ValueError, match="source and dest records must be of different read ordinals!"
    ):
        set_mate_info(r1, r2)


def test_set_mate_info_raises_when_second_rec_is_supplementary() -> None:
    """Test set_mate_info raises an exception when the second record is supplementary."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="x", read_num=2)
    r2.is_supplementary = True
    with pytest.raises(ValueError, match="Mate info must be set from a non-supplementary source!"):
        set_mate_info(r1, r2)


def test_set_mate_info_raises_mismatched_query_names() -> None:
    """Test set_mate_info raises an exception for mismatched query names."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="y", read_num=2)
    with pytest.raises(
        ValueError, match="Cannot set mate info on alignments with different query names!"
    ):
        set_mate_info(r1, r2)


def test_set_mate_info_both_unmapped() -> None:
    """Test set_mate_info sets mate info for two unmapped records."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair()
    assert r1.is_unmapped is True
    assert r2.is_unmapped is True

    set_mate_info(r1, r2)

    for rec in (r1, r2):
        assert rec.reference_id == sam.NO_REF_INDEX
        assert rec.reference_name is None
        assert rec.reference_start == sam.NO_REF_POS
        assert rec.next_reference_id == sam.NO_REF_INDEX
        assert rec.next_reference_name is None
        assert rec.next_reference_start == sam.NO_REF_POS
        assert not rec.has_tag("MC")
        assert rec.has_tag("MQ")
        assert rec.get_tag("MQ") == 0
        assert rec.has_tag("ms")
        assert rec.get_tag("ms") == 3000
        assert rec.template_length == 0
        assert rec.is_proper_pair is False

    # NB: unmapped records are forward until proven otherwise
    assert r1.is_forward is True
    assert r2.is_forward is True
    assert r1.mate_is_forward is True
    assert r2.mate_is_forward is True


def test_set_mate_info_one_unmapped() -> None:
    """Test set_mate_info sets mate info for one mapped and one unmapped records."""
    builder = SamBuilder()
    r1_mapped, r2_unmapped = builder.add_pair(chrom="chr1", start1=200, strand1="-")
    r1_unmapped, r2_mapped = builder.add_pair(chrom="chr1", start2=200, strand2="-")

    for mapped, unmapped in [(r1_mapped, r2_unmapped), (r2_mapped, r1_unmapped)]:
        assert mapped.is_mapped is True
        assert unmapped.is_unmapped is True

        set_mate_info(mapped, unmapped)

        assert mapped.reference_id == mapped.header.get_tid("chr1")
        assert mapped.reference_name == "chr1"
        assert mapped.reference_start == 200
        assert mapped.next_reference_id == sam.NO_REF_INDEX
        assert mapped.next_reference_name is None
        assert mapped.next_reference_start == sam.NO_REF_POS
        assert not mapped.has_tag("MC")
        assert mapped.has_tag("MQ")
        assert mapped.get_tag("MQ") == 0
        assert mapped.has_tag("ms")
        assert mapped.get_tag("ms") == 3000
        assert mapped.template_length == 0
        assert mapped.is_forward is False
        assert mapped.is_proper_pair is False
        assert mapped.mate_is_forward is True

        assert unmapped.reference_id == sam.NO_REF_INDEX
        assert unmapped.reference_name is None
        assert unmapped.reference_start == sam.NO_REF_POS
        assert unmapped.next_reference_id == unmapped.header.get_tid("chr1")
        assert unmapped.next_reference_name == "chr1"
        assert unmapped.next_reference_start == 200
        assert unmapped.has_tag("MC")
        assert unmapped.get_tag("MC") == "100M"
        assert unmapped.has_tag("MQ")
        assert unmapped.get_tag("MQ") == 60
        assert unmapped.has_tag("ms")
        assert unmapped.get_tag("ms") == 3000
        assert unmapped.template_length == 0
        assert unmapped.is_forward is True
        assert unmapped.is_proper_pair is False
        assert unmapped.mate_is_forward is False


def test_set_mate_info_both_mapped() -> None:
    """Test set_mate_info sets mate info for two mapped records."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=200, start2=300)
    assert r1.is_mapped is True
    assert r2.is_mapped is True

    set_mate_info(r1, r2)

    for rec in (r1, r2):
        assert rec.reference_id == builder.header.get_tid("chr1")
        assert rec.reference_name == "chr1"
        assert rec.next_reference_id == builder.header.get_tid("chr1")
        assert rec.next_reference_name == "chr1"
        assert rec.has_tag("MC")
        assert rec.get_tag("MC") == "100M"
        assert rec.has_tag("MQ")
        assert rec.get_tag("MQ") == 60
        assert rec.has_tag("ms")
        assert rec.get_tag("ms") == 3000
        assert rec.is_proper_pair is True

    assert r1.reference_start == 200
    assert r1.next_reference_start == 300
    assert r2.reference_start == 300
    assert r2.next_reference_start == 200
    assert r1.template_length == 200
    assert r2.template_length == -200
    assert r1.is_forward is True
    assert r2.is_reverse is True
    assert r1.mate_is_reverse is True
    assert r2.mate_is_forward is True


def test_set_mate_info_on_secondary() -> None:
    """Test set_mate_info_on_secondary sets mate info for a secondary record."""
    builder = SamBuilder()
    secondary, primary = builder.add_pair()
    secondary.is_secondary = True

    assert secondary.is_unmapped is True
    assert primary.is_unmapped is True

    set_mate_info_on_secondary(secondary, primary)

    assert secondary.reference_id == sam.NO_REF_INDEX
    assert secondary.reference_name is None
    assert secondary.reference_start == sam.NO_REF_POS
    assert secondary.next_reference_id == sam.NO_REF_INDEX
    assert secondary.next_reference_name is None
    assert secondary.next_reference_start == sam.NO_REF_POS
    assert not secondary.has_tag("MC")
    assert secondary.has_tag("MQ")
    assert secondary.get_tag("MQ") == 0
    assert secondary.has_tag("ms")
    assert secondary.get_tag("ms") == 3000
    assert secondary.template_length == 0
    assert secondary.is_proper_pair is False

    # NB: unmapped records are forward until proven otherwise
    assert secondary.is_forward is True
    assert secondary.mate_is_forward is True


def test_set_mate_info_on_secondary_raises_for_secondary_or_supp_rec2() -> None:
    """Test that set_mate_info_on_secondary raises an exception if rec2 is secondary or supp."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="x", read_num=2)
    r2.is_secondary = True
    with pytest.raises(
        ValueError, match="The mate primary must not be secondary or supplementary!"
    ):
        set_mate_info_on_secondary(r1, r2)
    r2.is_secondary = False
    r2.is_supplementary = True
    with pytest.raises(
        ValueError, match="The mate primary must not be secondary or supplementary!"
    ):
        set_mate_info_on_secondary(r1, r2)


def test_set_mate_info_on_secondary_raises_for_non_secondary_rec1() -> None:
    """Test that set_mate_info_on_secondary raises an exception if rec1 is not secondary."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="x", read_num=2)
    with pytest.raises(
        ValueError, match="Cannot set mate info on an alignment not marked as secondary!"
    ):
        set_mate_info_on_secondary(r1, r2)


def test_set_mate_info_on_supplementary() -> None:
    """Test set_mate_info_on_supplementary sets mate info for a supplementary record."""
    builder = SamBuilder()
    supplementary, primary = builder.add_pair()
    supplementary.is_supplementary = True

    assert supplementary.is_unmapped is True
    assert primary.is_unmapped is True

    set_mate_info_on_supplementary(supplementary, primary)

    assert supplementary.reference_id == sam.NO_REF_INDEX
    assert supplementary.reference_name is None
    assert supplementary.reference_start == sam.NO_REF_POS
    assert supplementary.next_reference_id == sam.NO_REF_INDEX
    assert supplementary.next_reference_name is None
    assert supplementary.next_reference_start == sam.NO_REF_POS
    assert not supplementary.has_tag("MC")
    assert supplementary.has_tag("MQ")
    assert supplementary.get_tag("MQ") == 0
    assert supplementary.has_tag("ms")
    assert supplementary.get_tag("ms") == 3000
    assert supplementary.template_length == 0
    assert supplementary.is_proper_pair is False

    # NB: unmapped records are forward until proven otherwise
    assert supplementary.is_forward is True
    assert supplementary.mate_is_forward is True


def test_set_mate_info_on_supplementary_raises_for_secondary_or_supp_rec2() -> None:
    """Test that set_mate_info_on_supplementary raises an exception if rec2 is secondary or supp."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="x", read_num=2)
    r2.is_secondary = True
    with pytest.raises(
        ValueError, match="The mate primary must not be secondary or supplementary!"
    ):
        set_mate_info_on_supplementary(r1, r2)
    r2.is_secondary = False
    r2.is_supplementary = True
    with pytest.raises(
        ValueError, match="The mate primary must not be secondary or supplementary!"
    ):
        set_mate_info_on_supplementary(r1, r2)


def test_set_mate_info_on_supplementary_raises_for_non_secondary_rec1() -> None:
    """Test that set_mate_info_on_supplementary raises an exception if rec1 is not supplementary."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="x", read_num=2)
    with pytest.raises(
        ValueError, match="Cannot set mate info on an alignment not marked as supplementary!"
    ):
        set_mate_info_on_supplementary(r1, r2)


def test_set_mate_info_on_supplementary_sets_additional_fields_for_primary_supplemental() -> None:
    """Tests that set_mate_info_on_supplementary sets additional fields for primary supplements."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="x", read_num=2)
    r1.is_supplementary = True
    r2.is_proper_pair = True
    r2.template_length = 100

    assert r1.is_proper_pair is False
    assert r1.template_length == 0
    set_mate_info_on_supplementary(r1, r2)
    assert r1.template_length == -100
    assert r1.is_proper_pair is True


def test_set_mate_info_on_supplementary_does_not_set_fields_for_secondary_supplemental() -> None:
    """Tests that set_mate_info_on_supplementary does not set fields for secondary supplements."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="x", read_num=2)
    r1.is_secondary = True
    r1.is_supplementary = True
    r2.is_proper_pair = True
    r2.template_length = 100

    assert not r1.is_proper_pair
    assert r1.template_length == 0
    set_mate_info_on_supplementary(r1, r2)
    assert not r1.is_proper_pair
    assert r1.template_length == 0


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_set_pair_info_raises_exception_for_mismatched_query_names() -> None:
    """Test that set_pair_info raises an exception for mismatched query names."""
    builder = SamBuilder()
    r1 = builder.add_single(name="x", read_num=1)
    r2 = builder.add_single(name="y", read_num=2)
    with pytest.raises(
        ValueError,
        match="Cannot set pair info on reads with different query names!",
    ):
        set_pair_info(r1, r2)


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_set_pair_info_both_mapped() -> None:
    """Test set_pair_info sets mate info for two mapped records."""
    builder = SamBuilder()
    r1, r2 = builder.add_pair(chrom="chr1", start1=200, start2=300)
    assert r1.is_mapped is True
    assert r2.is_mapped is True

    set_pair_info(r1, r2, proper_pair=False)

    for rec in (r1, r2):
        assert rec.reference_id == builder.header.get_tid("chr1")
        assert rec.reference_name == "chr1"
        assert rec.next_reference_id == builder.header.get_tid("chr1")
        assert rec.next_reference_name == "chr1"
        assert rec.has_tag("MC")
        assert rec.get_tag("MC") == "100M"
        assert rec.has_tag("MQ")
        assert rec.get_tag("MQ") == 60
        assert rec.has_tag("ms")
        assert rec.get_tag("ms") == 3000
        assert rec.is_proper_pair is False

    assert r1.reference_start == 200
    assert r1.next_reference_start == 300
    assert r2.reference_start == 300
    assert r2.next_reference_start == 200
    assert r1.template_length == 200
    assert r2.template_length == -200
    assert r1.is_forward is True
    assert r2.is_reverse is True
    assert r1.mate_is_reverse is True
    assert r2.mate_is_forward is True
