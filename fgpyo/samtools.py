"""
Type-Hinted Wrappers around pysam samtools dispatch functions.
--------------------------------------------------------------

Calls pysam samtools functions, with type hints for relevant parameters and return types.

Examples
~~~~~~~~
.. code-block:: python

   >>> from fgpyo import samtools
   >>> Path("example1.sorted.bam.bai").exists()
   False
   >>> samtools.sort(input=Path("example1.bam"), output=Path("example1.sorted.bam"))
   ''
   >>> samtools.index(input=Path("example1.sorted.bam"))
   ''
   >>> Path("example1.sorted.bam.bai").exists()
   True

Module Contents
~~~~~~~~~~~~~~~
The module contains the following public method definitions:
    - :class:`~fgpyo.samtools.dict` -- Wrapper around pysam call to samtools dict with type hints
        on inputs and return type
    - :class:`~fgpyo.samtools.sort` -- Wrapper around pysam call to samtools sort with type hints
        on inputs and return type
    - :class:`~fgpyo.samtools.faidx` -- Wrapper around pysam call to samtools faidx with type hints
        on inputs and return type
    - :class:`~fgpyo.samtools.index` -- Wrapper around pysam call to samtools index with type hints
        on inputs and return type
"""
import enum
from pathlib import Path
from typing import TYPE_CHECKING
from typing import List
from typing import Optional
from typing import Tuple

from fgpyo.sam import SamFileType
from fgpyo.sam import SamOrder


def pysam_fn(*args: str) -> str:
    """
    Type hinted import of an example function from the pysam samtools dispatcher.
    """
    pass


if TYPE_CHECKING:
    _pysam_dict = pysam_fn
    _pysam_sort = pysam_fn
    _pysam_faidx = pysam_fn
    _pysam_index = pysam_fn
else:
    from pysam import dict as _pysam_dict
    from pysam import faidx as _pysam_faidx
    from pysam import index as _pysam_index
    from pysam import sort as _pysam_sort


def dict(
    input: Path,
    output: Path,
    no_header: bool = False,
    alias: bool = False,
    assembly: Optional[str] = None,
    alt: Optional[Path] = None,
    species: Optional[str] = None,
    uri: Optional[str] = None,
) -> str:
    """
    Calls the `samtools` function `dict` using the pysam samtools dispatcher.

    Arguments will be formatted into the appropriate command-line call which will be invoked
    using the pysam dispatcher.

    Returns the stdout of the resulting call to pysam.dict()

    Args:
        input: Path to the FASTA files to generate a sequence dictionary for.
        output: Path to the file to write output to.
        no_header: If true will not print the @HD header line.
        assembly: The assembly for the AS tag.
        alias: Adds an AN tag with the same value as the SN tag, except that a 'chr' prefix is
            removed if SN has one or added if it does not. For mitochondria (i.e., when SN is “M”
            or “MT”, with or without a “chr” prefix), also adds the remaining combinations of
            “chr/M/MT” to the AN tag.
        alt: Add an AH tag to each sequence listed in the specified bwa-style .alt file. These
            files use SAM records to represent alternate locus sequences (as named in the QNAME
            field) and their mappings to the primary assembly.
        species: Specify the species for the SP tag.
        uri: Specify the URI for the UR tag. Defaults to the absolute path of ref.fasta.
    """

    args: List[str] = ["--output", str(output)]

    if no_header:
        args.append("--no-header")

    if alias:
        args.append("--alias")

    if assembly is not None:
        args.extend(["--assembly", assembly])

    if alt is not None:
        args.extend(["--alt", str(alt)])

    if species is not None:
        args.extend(["--species", species])

    if uri is not None:
        args.extend(["--uri", uri])

    args.append(str(input))

    return _pysam_dict(*args)


@enum.unique
class FaidxMarkStrand(enum.Enum):
    RevComp = "rc"
    No = "no"
    Sign = "sign"
    Custom = "custom"


def faidx(
    input: Path,
    output: Optional[Path] = None,
    length: int = 60,
    regions: Optional[List[str]] = None,
    region_file: Optional[Path] = None,
    fai_idx: Optional[Path] = None,
    gzi_idx: Optional[Path] = None,
    continue_if_non_existent: bool = False,
    fastq: bool = False,
    reverse_complement: bool = False,
    mark_strand: FaidxMarkStrand = FaidxMarkStrand.RevComp,
    custom_mark_strand: Optional[Tuple[str, str]] = None,
) -> str:
    """
    Calls the `samtools` function `faidx` using the pysam samtools dispatcher.

    Arguments will be formatted into the appropriate command-line call which will be invoked
    using the pysam dispatcher.

    Returns the stdout of the resulting call to pysam.faidx()

    Args:
        input: Path to the FAIDX files to index / read from.
        output: Path to the file to write FASTA output.
        length: Length of FASTA sequence line.
        regions: regions to extract from the FASTA file in samtools region format
            (<chrom>:<1-based start>-<1-based end>)
        region_file: Path to file containing regions to extract from the FASTA file in samtools
            region format (<chrom>:<1-based start>-<1-based end>). 1 region descriptor per line.
        fai_idx: Read/Write to specified FAI index file.
        gzi_idx: Read/Write to specified compressed file index (used with .gz files).
        continue_if_non_existent: If true continue qorking if a non-existent region is requested.
        fastq: Read FASTQ files and output extracted sequences in FASTQ format. Same as using
            samtools fqidx.
        reverse_complement: Output the sequence as the reverse complement. When this option is
            used, “/rc” will be appended to the sequence names. To turn this off or change the
            string appended, use the mark_strand parameter.
        mark_strand: Append strand indicator to sequence name. Type to append can be one of:
            FaidxMarkStrand.RevComp - Append '/rc' when writing the reverse complement. This is the
            default.

            FaidxMarkStrand.No - Do not append anything.

            FaidxMarkStrand.Sign - Append '(+)' for forward strand or '(-)' for reverse
            complement. This matches the output of “bedtools getfasta -s”.

            FaidxMarkStrand.Custom - custom,<custom_mark_strand[0]>,<custom_mark_strand[1]>
            Append string <pos> to names when writing the forward strand and <neg> when writing the
            reverse strand. Spaces are preserved, so it is possible to move the indicator into the
            comment part of the description line by including a leading space in the strings
            <custom_mark_strand[0]> and <custom_mark_strand[1]>.
        custom_mark_strand: The custom strand indicators to use in in the Custom MarkStrand
            setting. The first value of the tuple will be used as the positive strand indicator,
            the second value will be used as the negative strand indicator.
    """

    mark_strand_str: str
    if mark_strand == FaidxMarkStrand.Custom:
        assert custom_mark_strand is not None, (
            "Cannot use custom mark strand without providing the custom strand indicators to "
            + "`custom_mark_string`"
        )
        mark_strand_str = f"{mark_strand.value},{custom_mark_strand[0]},{custom_mark_strand[1]}"
    else:
        mark_strand_str = mark_strand.value

    args: List[str] = ["--length", str(length), "--mark-strand", mark_strand_str]

    if output is not None:
        args.extend(["--output", str(output)])

    if continue_if_non_existent:
        args.append("--continue")
    if reverse_complement:
        args.append("--reverse-complement")
    if fastq:
        args.append("--fastq")

    if fai_idx is not None:
        args.extend(["--fai-idx", str(fai_idx)])

    if gzi_idx is not None:
        args.extend(["--gzi-idx", str(gzi_idx)])

    if region_file is not None:
        args.extend(["--region-file", str(region_file)])

    args.append(str(input))

    if regions is not None:
        args.extend(regions)

    return _pysam_faidx(*args)


@enum.unique
class SamIndexType(enum.Enum):
    BAI = "-b"
    CSI = "-c"


def index(
    input: Path,
    # See https://github.com/pysam-developers/pysam/issues/1155
    # inputs: List[Path], Cant currently accept multiple
    output: Optional[Path] = None,
    threads: int = 0,
    index_type: SamIndexType = SamIndexType.BAI,
    csi_index_size: int = 14,
) -> str:
    """
    Calls the `samtools` function `index` using the pysam samtools dispatcher.

    Arguments will be formatted into the appropriate command-line call which will be invoked
    using the pysam dispatcher.

    Returns the stdout of the resulting call to pysam.index()

    Args:
        input: Path to the SAM/BAM/CRAM file to index.
        output: Path to the file to write output. (Currently may only be used when exactly one
            alignment file is being indexed.)
        threads: Number of input/output compression threads to use in addition to main thread.
        index_type: The type of index file to produce when indexing.
        csi_index_size: Sets the minimum interval size of CSI indices to 2^INT.
    """

    # assert len(inputs) >= 1, "Must provide at least one input to samtools index."

    # if len(inputs) != 1:
    #     assert (
    #         output is None
    #     ), "Output currently can only be used if there is exactly one input file being indexed"
    #     args = ["-M"]
    # else:
    #     args = []
    args = []

    if index_type != SamIndexType.BAI:
        args.append(index_type.value)

    if index_type == SamIndexType.CSI:
        args.extend(["-m", str(csi_index_size)])
    args.extend(["-@", str(threads)])
    args.append(str(input))
    if output is not None:
        args.extend(["-o", str(output)])

    return _pysam_index(*args)


def sort(
    input: Path,
    output: Path,
    index_output: bool = True,
    sort_unmapped_reads: bool = False,
    kmer_size: int = 20,
    compression_level: Optional[int] = None,
    memory_per_thread: str = "768MB",
    sort_order: SamOrder = SamOrder.Coordinate,
    sort_tag: Optional[str] = None,
    output_format: SamFileType = SamFileType.BAM,
    tempfile_prefix: Optional[str] = None,
    threads: int = 1,
    no_pg: bool = False,
) -> str:
    """
    Calls the `samtools` function sort using the pysam samtools dispatcher.

    Arguments will be formatted into the appropriate command-line call which will be invoked
    using the pysam dispatcher.

    Returns the stdout of the resulting call to pysam.sort()

    Args:
        input: Path to the SAM/BAM/CRAM file to sort.
        output: Path to the file to write output.
        index_output: If true, creates an index for the output file.
        sort_unmapped_reads: If true, sort unmapped reads by their sequence minimizer, reverse
            complementing where appropriate. This has the effect of collating some similar data
            together, improving the compressibility of the unmapped sequence. The minimiser kmer
            size is adjusted using the ``kmer_size`` option. Note data compressed in this manner
            may need to be name collated prior to conversion back to fastq.

            Mapped sequences are sorted by chromosome and position.
        kmer_size: the kmer-size to be used if sorting unmapped reads.
        compression_level: The compression level to be used in the final output file.
        memory_per_thread: Approximately the maximum required memory per thread, specified either
            in bytes or with a K, M, or G suffix.

            To prevent sort from creating a huge number of temporary files, it enforces a minimum
            value of 1M for this setting.
        sort_order: The sort order to use when sorting the file.
        sort_tag: The tag to use to use to sort the SAM/BAM/CRAM records. Will be sorted by
            this tag first, followed by position (or name, depending on ``sort_order``
            provided).
        output_format: the output file format to write the results as.
            By default, will try to select a format based on the ``output`` filename extension;
            if no format can be deduced, bam is selected.
        tempfile_prefix: The prefix to use for temporary files. Resulting files will be in
            format PREFIX.nnnn.bam, or if the specified PREFIX is an existing directory, to
            PREFIX/samtools.mmm.mmm.tmp.nnnn.bam, where mmm is unique to this invocation of the
            sort command.

            By default, any temporary files are written alongside the output file, as
            out.bam.tmp.nnnn.bam, or if output is to standard output, in the current directory
            as samtools.mmm.mmm.tmp.nnnn.bam.
        threads: The number of threads to use when sorting. By default, operation is
            single-threaded.
        no_pg: If true, will not add a @PG line to the header of the output file.
    """

    output_string = (
        f"{output}##idx##{output}{output_format.index_extension}"
        if index_output and output_format.index_extension is not None
        else str(output)
    )

    args = ["-m", memory_per_thread, "-O", output_format._name_, "-@", str(threads)]

    if sort_unmapped_reads:
        args.extend(["-M", "-K", str(kmer_size)])

    if compression_level is not None:
        args.extend(["-I", str(compression_level)])

    if sort_order == SamOrder.QueryName:
        args.append("-n")
    elif sort_order == SamOrder.TemplateCoordinate:
        args.append("--template-coordinate")
    else:
        assert (
            sort_order == SamOrder.Coordinate
        ), "Sort order to samtools sort cannot be Unknown or Unsorted"

    if sort_tag is not None:
        args.extend(["-t", sort_tag])

    if tempfile_prefix is not None:
        args.extend(["-T", tempfile_prefix])

    if no_pg:
        args.append("--no-PG")

    args.extend(["-o", output_string, str(input)])

    return _pysam_sort(*args)
