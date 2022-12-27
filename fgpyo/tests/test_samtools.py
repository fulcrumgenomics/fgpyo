from pathlib import Path
from typing import List
from typing import Optional

import bgzip
import pytest
from pysam.utils import SamtoolsError

from fgpyo import sam
from fgpyo import samtools
from fgpyo.sam import SamFileType
from fgpyo.sam import SamOrder
from fgpyo.sam.builder import SamBuilder
from fgpyo.samtools import FaidxMarkStrand
from fgpyo.samtools import SamIndexType

EXAMPLE_DICT_FASTA: str = """\
>chr1
GATTACATTTGAGAGA
>chr2
CCCCTACCCACCC
>chr1_alt
GATTACATGAGAGA
>chr2_alt
CCCCTACCACCC
"""

EXPECTED_DICT: str = """\
@HD	VN:1.0	SO:unsorted
@SQ	SN:chr1	LN:16	M5:0b2bf1b29cf5338d75a8feb8c8a3784b	UR:consistent_location
@SQ	SN:chr2	LN:13	M5:87afe3395654b1fe1443b54490c47871	UR:consistent_location
@SQ	SN:chr1_alt	LN:14	M5:23ce480f016f77dfb29d3c17aa98f567	UR:consistent_location
@SQ	SN:chr2_alt	LN:12	M5:2ee663b21d249ebecaa9ffbdb6e0b970	UR:consistent_location
"""

HEADERLESS_DICT: str = """\
@SQ	SN:chr1	LN:16	M5:0b2bf1b29cf5338d75a8feb8c8a3784b	UR:consistent_location
@SQ	SN:chr2	LN:13	M5:87afe3395654b1fe1443b54490c47871	UR:consistent_location
@SQ	SN:chr1_alt	LN:14	M5:23ce480f016f77dfb29d3c17aa98f567	UR:consistent_location
@SQ	SN:chr2_alt	LN:12	M5:2ee663b21d249ebecaa9ffbdb6e0b970	UR:consistent_location
"""

OTHER_TAG_DICT: str = """\
@HD	VN:1.0	SO:unsorted
@SQ	SN:chr1	LN:16	M5:0b2bf1b29cf5338d75a8feb8c8a3784b	AN:1	UR:consistent_location	AS:test1	SP:test3
@SQ	SN:chr2	LN:13	M5:87afe3395654b1fe1443b54490c47871	AN:2	UR:consistent_location	AS:test1	SP:test3
@SQ	SN:chr1_alt	LN:14	M5:23ce480f016f77dfb29d3c17aa98f567	AH:*	AN:1_alt	UR:consistent_location	AS:test1	SP:test3
@SQ	SN:chr2_alt	LN:12	M5:2ee663b21d249ebecaa9ffbdb6e0b970	AH:*	AN:2_alt	UR:consistent_location	AS:test1	SP:test3
"""  # noqa: E501


@pytest.fixture
def example_dict_fasta(tmp_path: Path) -> Path:
    outfile = tmp_path / "example.fa"

    with outfile.open("w") as out_fh:
        out_fh.write(EXAMPLE_DICT_FASTA)

    return outfile


def test_dict_produces_sequence_dict(
    tmp_path: Path,
    example_dict_fasta: Path,
) -> None:
    output_access = tmp_path / "example.dict"
    assert not output_access.exists()
    samtools.dict(input=example_dict_fasta, output=output_access, uri="consistent_location")
    assert output_access.exists()

    output_contents: str
    with output_access.open("r") as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == EXPECTED_DICT


def test_dict_no_header_works(
    tmp_path: Path,
    example_dict_fasta: Path,
) -> None:
    output_access = tmp_path / "example.dict"
    assert not output_access.exists()
    samtools.dict(
        input=example_dict_fasta, output=output_access, no_header=True, uri="consistent_location"
    )
    assert output_access.exists()

    output_contents: str
    with output_access.open("r") as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == HEADERLESS_DICT


ALT_FILE: str = """\
chr1_alt	0	chr1	1	30	7M2D7M	*	0	0	*	*	NM:i:2
chr2_alt	0	chr2	1	30	6M1D6M	*	0	0	*	*	NM:i:1
"""


@pytest.fixture
def bwa_style_alt(tmp_path: Path) -> Path:
    outfile = tmp_path / "example.alt"

    with outfile.open("w") as out_fh:
        out_fh.write(ALT_FILE)

    return outfile


def test_dict_other_tags_work(
    tmp_path: Path,
    example_dict_fasta: Path,
    bwa_style_alt: Path,
) -> None:
    output_access = tmp_path / "example.dict"
    assert not output_access.exists()
    samtools.dict(
        input=example_dict_fasta,
        output=output_access,
        alias=True,
        assembly="test1",
        alt=bwa_style_alt,
        species="test3",
        uri="consistent_location",
    )
    assert output_access.exists()

    output_contents: str
    with output_access.open("r") as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == OTHER_TAG_DICT


EXAMPLE_FAIDX_FASTA: str = """\
>chr1
GATTACATTTGAGAGA
>chr2
CCCCTACCCACCC
"""

SUBSET_FASTA_TEMPLATE: str = """\
>chr1:1-7{mark_strand}
GATTACA
>chr2:8-13{mark_strand}
CCACCC
"""
SUBSET_FASTA: str = SUBSET_FASTA_TEMPLATE.format(mark_strand="")

WRAPPED_SUBSET_FASTA: str = """\
>chr1:1-7
GATTA
CA
>chr2:8-13
CCACC
C
"""


@pytest.fixture
def example_faidx_fasta(tmp_path: Path) -> Path:
    outfile = tmp_path / "example.fa"

    with outfile.open("w") as out_fh:
        out_fh.write(EXAMPLE_FAIDX_FASTA)

    return outfile


def test_faidx_produces_functional_index(
    tmp_path: Path,
    example_faidx_fasta: Path,
) -> None:
    output_index_expected = Path(f"{example_faidx_fasta}.fai")

    # Make sure we're producing the index
    assert not output_index_expected.exists()
    samtools.faidx(input=example_faidx_fasta)
    assert output_index_expected.exists()

    output_access = tmp_path / "output_subset.fa"
    # Make sure the index is functional
    samtools.faidx(
        input=example_faidx_fasta, output=output_access, regions=["chr1:1-7", "chr2:8-13"]
    )

    output_contents: str
    with output_access.open("r") as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == SUBSET_FASTA


def test_faidx_fails_if_non_existent_region_requested(
    tmp_path: Path,
    example_faidx_fasta: Path,
) -> None:
    with pytest.raises(SamtoolsError):
        output_index_expected = Path(f"{example_faidx_fasta}.fai")

        # Make sure we're producing the index
        assert not output_index_expected.exists()
        samtools.faidx(input=example_faidx_fasta)
        assert output_index_expected.exists()

        output_access = tmp_path / "output_subset.fa"
        # Make sure the index is functional
        samtools.faidx(
            input=example_faidx_fasta, output=output_access, regions=["chr3:1-4", "chr1:1-7"]
        )


def test_faidx_passes_if_non_existent_region_requested_when_continue_passed(
    tmp_path: Path,
    example_faidx_fasta: Path,
) -> None:
    output_index_expected = Path(f"{example_faidx_fasta}.fai")

    assert not output_index_expected.exists()
    samtools.faidx(input=example_faidx_fasta)
    assert output_index_expected.exists()

    output_access = tmp_path / "output_subset.fa"
    samtools.faidx(
        input=example_faidx_fasta,
        output=output_access,
        continue_if_non_existent=True,
        regions=["chr3:1-4", "chr1:1-7"],
    )


def test_faidx_regions_and_regions_file_result_in_same_thing(
    tmp_path: Path,
    example_faidx_fasta: Path,
) -> None:
    output_index_expected = Path(f"{example_faidx_fasta}.fai")

    # Make sure we're producing the index
    assert not output_index_expected.exists()
    samtools.faidx(input=example_faidx_fasta)
    assert output_index_expected.exists()

    output_access = tmp_path / "output_subset.fa"
    # Make sure the index is functional

    regions = ["chr1:1-7", "chr2:8-13"]

    region_file = tmp_path / "regions.txt"
    with region_file.open("w") as region_fh:
        region_fh.writelines([f"{region}\n" for region in regions])

    samtools.faidx(input=example_faidx_fasta, output=output_access, regions=regions)

    manually_passed_output_contents: str
    with output_access.open("r") as subset_fasta:
        manually_passed_output_contents = subset_fasta.read()

    samtools.faidx(input=example_faidx_fasta, output=output_access, region_file=region_file)

    file_passed_output_contents: str
    with output_access.open("r") as subset_fasta:
        file_passed_output_contents = subset_fasta.read()

    assert manually_passed_output_contents == file_passed_output_contents


def test_length_parameter(
    tmp_path: Path,
    example_faidx_fasta: Path,
) -> None:
    output_index_expected = Path(f"{example_faidx_fasta}.fai")

    # Make sure we're producing the index
    assert not output_index_expected.exists()
    samtools.faidx(
        input=example_faidx_fasta,
    )
    assert output_index_expected.exists()

    output_access = tmp_path / "output_subset.fa"
    # Make sure the index is functional
    samtools.faidx(
        input=example_faidx_fasta,
        output=output_access,
        regions=["chr1:1-7", "chr2:8-13"],
        length=5,
    )

    output_contents: str
    with output_access.open() as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == WRAPPED_SUBSET_FASTA


RC_SUBSET_FASTA: str = """\
>chr1:1-7{mark_strand}
TGTAATC
>chr2:8-13{mark_strand}
GGGTGG
"""


def test_rc_parameter(
    tmp_path: Path,
    example_faidx_fasta: Path,
) -> None:
    output_index_expected = Path(f"{example_faidx_fasta}.fai")

    # Make sure we're producing the index
    assert not output_index_expected.exists()
    samtools.faidx(
        input=example_faidx_fasta,
    )
    assert output_index_expected.exists()

    output_access = tmp_path / "output_subset.fa"
    # Make sure the index is functional
    samtools.faidx(
        input=example_faidx_fasta,
        output=output_access,
        reverse_complement=True,
        regions=["chr1:1-7", "chr2:8-13"],
    )

    output_contents: str
    with output_access.open() as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == RC_SUBSET_FASTA.format(mark_strand="/rc")


@pytest.mark.parametrize(
    argnames=["mark_strand", "expected_fwd_mark_strand", "expected_rev_mark_strand"],
    argvalues=[
        (FaidxMarkStrand.RevComp, "", "/rc"),
        (FaidxMarkStrand.No, "", ""),
        (FaidxMarkStrand.Sign, "(+)", "(-)"),
        (FaidxMarkStrand.Custom, "ex1a", "ex1b"),
        (FaidxMarkStrand.Custom, "ex2a", "ex2b"),
    ],
    ids=["rev comp", "no", "sign", "custom1", "custom2"],
)
def test_mark_strand_parameters(
    tmp_path: Path,
    example_faidx_fasta: Path,
    mark_strand: FaidxMarkStrand,
    expected_fwd_mark_strand: str,
    expected_rev_mark_strand: str,
) -> None:
    output_index_expected = Path(f"{example_faidx_fasta}.fai")

    # Make sure we're producing the index
    assert not output_index_expected.exists()
    samtools.faidx(
        input=example_faidx_fasta,
    )
    assert output_index_expected.exists()

    output_access = tmp_path / "output_subset.fa"
    # Make sure the index is functional
    samtools.faidx(
        input=example_faidx_fasta,
        output=output_access,
        reverse_complement=False,
        mark_strand=mark_strand,
        custom_mark_strand=(expected_fwd_mark_strand, expected_rev_mark_strand),
        regions=["chr1:1-7", "chr2:8-13"],
    )
    output_contents: str
    with output_access.open() as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == SUBSET_FASTA_TEMPLATE.format(mark_strand=expected_fwd_mark_strand)

    samtools.faidx(
        input=example_faidx_fasta,
        output=output_access,
        reverse_complement=True,
        mark_strand=mark_strand,
        custom_mark_strand=(expected_fwd_mark_strand, expected_rev_mark_strand),
        regions=["chr1:1-7", "chr2:8-13"],
    )

    with output_access.open() as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == RC_SUBSET_FASTA.format(mark_strand=expected_rev_mark_strand)


EXAMPLE_FASTQ: str = """\
@chr1
GATTACATTTGAGAGA
+
;;;;;;;;;;;;;;;;
@chr2
CCCCTACCCACCC
+
;;;;;;;;;;;;;
"""

SUBSET_FASTQ: str = """\
@chr1:1-7
GATTACA
+
;;;;;;;
@chr2:8-13
CCACCC
+
;;;;;;
"""


@pytest.fixture
def example_fastq(tmp_path: Path) -> Path:
    outfile = tmp_path / "example.fq"

    with outfile.open("w") as out_fh:
        out_fh.write(EXAMPLE_FASTQ)

    return outfile


def test_fastq_parameter(
    tmp_path: Path,
    example_fastq: Path,
) -> None:
    output_index_expected = Path(f"{example_fastq}.fai")

    # Make sure we're producing the index
    assert not output_index_expected.exists()
    samtools.faidx(
        input=example_fastq,
        fastq=True,
    )
    assert output_index_expected.exists()

    output_access = tmp_path / "output_subset.fq"
    # Make sure the index is functional
    samtools.faidx(
        input=example_fastq,
        output=output_access,
        regions=["chr1:1-7", "chr2:8-13"],
        fastq=True,
    )

    output_contents: str
    with output_access.open() as subset_fasta:
        output_contents = subset_fasta.read()

    assert output_contents == SUBSET_FASTQ


@pytest.fixture
def example_faidx_fasta_gz(tmp_path: Path) -> Path:
    outfile = tmp_path / "example.fa.gz"

    with outfile.open(mode="wb") as out_fh:
        with bgzip.BGZipWriter(out_fh) as fh:
            fh.write(bytes(EXAMPLE_FAIDX_FASTA, "Utf-8"))

    return outfile


def test_index_outputs(
    tmp_path: Path,
    example_faidx_fasta: Path,
    example_faidx_fasta_gz: Path,
) -> None:
    example_fai = Path(f"{example_faidx_fasta}.fai")

    # Make sure we're producing the index
    assert not example_fai.exists()
    samtools.faidx(
        input=example_faidx_fasta,
        fai_idx=example_fai,
    )
    assert example_fai.exists()

    output_access = tmp_path / "output_subset.fa"
    # Make sure the index is functional
    samtools.faidx(
        input=example_faidx_fasta,
        output=output_access,
        regions=["chr1:1-7", "chr2:8-13"],
        fai_idx=example_fai,
    )

    output_contents: str
    with output_access.open() as subset_fasta:
        output_contents = subset_fasta.read()
    assert output_contents == SUBSET_FASTA

    example_gzi = Path(f"{example_faidx_fasta_gz}.gzi")
    assert not example_gzi.exists()
    samtools.faidx(
        input=example_faidx_fasta_gz,
        gzi_idx=example_gzi,
    )
    assert example_gzi.exists()

    output_access = tmp_path / "output_subset.fa"
    # Make sure the index is functional
    samtools.faidx(
        input=example_faidx_fasta,
        output=output_access,
        regions=["chr1:1-7", "chr2:8-13"],
        gzi_idx=example_gzi,
    )

    compressed_output_contents: str
    with output_access.open() as subset_fasta:
        compressed_output_contents = subset_fasta.read()

    assert compressed_output_contents == SUBSET_FASTA


@pytest.mark.parametrize(
    argnames=["index_type"],
    argvalues=[
        (SamIndexType.BAI,),
        (SamIndexType.CSI,),
    ],
    ids=["BAI", "CSI"],
)
def test_index_works_with_one_input(
    tmp_path: Path,
    index_type: SamIndexType,
) -> None:
    builder = SamBuilder(sort_order=SamOrder.Coordinate)
    builder.add_pair(name="test1", chrom="chr1", start1=4000, start2=4300)
    builder.add_pair(
        name="test2", chrom="chr1", start1=5000, start2=4700, strand1="-", strand2="+"
    )
    builder.add_pair(name="test3", chrom="chr2", start1=4000, start2=4300)
    builder.add_pair(name="test4", chrom="chr5", start1=4000, start2=4300)

    # At the moment sam builder doesnt support generating CRAM and SAM formats, so for now we're
    # only testing on BAMs
    input_file = tmp_path / "test_input.bam"
    builder.to_path(input_file)

    output_index_expected = Path(f"{input_file}.{index_type._name_.lower()}")

    # Make sure we're producing the index
    assert not output_index_expected.exists()
    # samtools.index(inputs=[input_file], index_type=index_type)
    samtools.index(input=input_file, index_type=index_type)
    assert output_index_expected.exists()


# Can't accept multiple inputs at the moment.
# See https://github.com/pysam-developers/pysam/issues/1155
# @pytest.mark.parametrize(
#     argnames=["index_type"],
#     argvalues=[
#         (SamIndexType.BAI,),
#         (SamIndexType.CSI,),
#     ],
#     ids=["BAI", "CSI"],
# )
# def test_index_works_with_multiple_inputs(
#     tmp_path: Path,
#     index_type: SamIndexType,
# ) -> None:
#     builder = SamBuilder(sort_order=SamOrder.Coordinate)
#     builder.add_pair(name="test1", chrom="chr1", start1=4000, start2=4300)
#     builder.add_pair(
#         name="test2", chrom="chr1", start1=5000, start2=4700, strand1="-", strand2="+"
#     )
#     builder.add_pair(name="test3", chrom="chr2", start1=4000, start2=4300)
#     builder.add_pair(name="test4", chrom="chr5", start1=4000, start2=4300)

#     # At the moment sam builder doesnt support generating CRAM and SAM formats, so for now we're
#     # only testing on BAMs
#     input_file1 = tmp_path / "test_input1.bam"
#     builder.to_path(input_file1)
#     input_file2 = tmp_path / "test_input2.bam"
#     builder.to_path(input_file2)

#     inputs = [
#         input_file1,
#         input_file2,
#     ]

#     # Make sure we're producing the indices
#     for input in inputs:
#         output_index_expected = Path(f"{input}.{index_type._name_.lower()}")
#         assert not output_index_expected.exists()

#     samtools.index(inputs=inputs, index_type=index_type)
#     for input in inputs:
#         output_index_expected = Path(f"{input}.{index_type._name_.lower()}")
#         assert output_index_expected.exists()


@pytest.mark.parametrize(
    argnames=["file_type"],
    argvalues=[
        (SamFileType.SAM,),
        (SamFileType.BAM,),
        (SamFileType.CRAM,),
    ],
    ids=["SAM", "BAM", "CRAM"],
)
@pytest.mark.parametrize(
    argnames=["index_output"],
    argvalues=[
        (True,),
        (False,),
    ],
    ids=["indexed", "not_indexed"],
)
@pytest.mark.parametrize(
    argnames=["sort_order", "expected_name_order"],
    argvalues=[
        (SamOrder.Coordinate, ["test2", "test3", "test4", "test1"]),
        (SamOrder.QueryName, ["test1", "test2", "test3", "test4"]),
        (SamOrder.TemplateCoordinate, ["test2", "test3", "test4", "test1"]),
    ],
    ids=["Coordinate sorting", "Query name sorting", "Template Sorted"],
)
def test_sort_types(
    tmp_path: Path,
    file_type: SamFileType,
    index_output: bool,
    sort_order: Optional[SamOrder],
    expected_name_order: List[str],
) -> None:

    builder = SamBuilder(sort_order=SamOrder.Unsorted)
    builder.add_pair(
        name="test3", chrom="chr1", start1=5000, start2=4700, strand1="-", strand2="+"
    )
    builder.add_pair(name="test2", chrom="chr1", start1=4000, start2=4300)
    builder.add_pair(name="test1", chrom="chr5", start1=4000, start2=4300)
    builder.add_pair(name="test4", chrom="chr2", start1=4000, start2=4300)

    input_file = tmp_path / "test_input.bam"
    output_file = tmp_path / f"test_output{file_type.extension}"

    builder.to_path(input_file)

    samtools.sort(
        input=input_file,
        output=output_file,
        index_output=index_output,
        sort_order=sort_order,
    )
    with sam.reader(output_file) as in_bam:
        for name in expected_name_order:
            read1 = next(in_bam)
            assert (
                name == read1.query_name
            ), "Position based read sort order did not match expectation"
            read2 = next(in_bam)
            assert (
                name == read2.query_name
            ), "Position based read sort order did not match expectation"

    if index_output and file_type != SamFileType.SAM:
        assert Path(f"{output_file}{file_type.index_extension}")
