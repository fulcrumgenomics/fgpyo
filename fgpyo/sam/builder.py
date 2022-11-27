"""
Classes for generating SAM and BAM files and records for testing
----------------------------------------------------------------

This module contains utility classes for the generation of SAM and BAM files and
alignment records, for use in testing.

The module contains the following public classes:

    - :class:`~fgpyo.sam.builder.SamBuilder` -- A builder class that allows the accumulation
        of alignment records and access as a list and writing to file.
"""
from array import array
from pathlib import Path
from random import Random
from tempfile import NamedTemporaryFile
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import pysam
from pysam import AlignedSegment
from pysam import AlignmentHeader

from fgpyo import sam


class SamBuilder:
    """Builder for constructing one or more sam records (AlignmentSegments in pysam terms).

    Provides the ability to manufacture records from minimal arguments, while generating
    any remaining attributes to ensure a valid record.

    A builder is constructed with a handful of defaults including lengths for generated R1s
    and R2s, the default base quality score to use, a sequence dictionary and a single read group.

    Records are then added using the :func:`~fgpyo.builder.SamBuilder.add_pair` method.
    Once accumulated the records can be accessed in the order in which they were created through
    the :func:`~fgpyo.builder.SamBuilder.to_unsorted_list` function, or in a list sorted
    by coordinate order via :func:`~fgpyo.builder.SamBuilder.to_sorted_list`.  The latter
    creates a temporary file to do the sorting and is somewhat slower as a result.  Lastly, the
    records can be written to a temporary file using
    :func:`~fgpyo.builder.SamBuilder.to_path`.
    """

    # The default read one length
    DEFAULT_R1_LENGTH: int = 100

    # The default read two length
    DEFAULT_R2_LENGTH: int = 100

    @staticmethod
    def default_sd() -> List[Dict[str, Any]]:
        """Generates the sequence dictionary that is used by default by SamBuilder.

        Matches the names and lengths of the HG19 reference in use in production.

        Returns:
            A new copy of the sequence dictionary as a list of dictionaries, one per chromosome.
        """
        return [
            {"SN": "chr1", "LN": 249250621},
            {"SN": "chr2", "LN": 243199373},
            {"SN": "chr3", "LN": 198022430},
            {"SN": "chr4", "LN": 191154276},
            {"SN": "chr5", "LN": 180915260},
            {"SN": "chr6", "LN": 171115067},
            {"SN": "chr7", "LN": 159138663},
            {"SN": "chr8", "LN": 146364022},
            {"SN": "chr9", "LN": 141213431},
            {"SN": "chr10", "LN": 135534747},
            {"SN": "chr11", "LN": 135006516},
            {"SN": "chr12", "LN": 133851895},
            {"SN": "chr13", "LN": 115169878},
            {"SN": "chr14", "LN": 107349540},
            {"SN": "chr15", "LN": 102531392},
            {"SN": "chr16", "LN": 90354753},
            {"SN": "chr17", "LN": 81195210},
            {"SN": "chr18", "LN": 78077248},
            {"SN": "chr19", "LN": 59128983},
            {"SN": "chr20", "LN": 63025520},
            {"SN": "chr21", "LN": 48129895},
            {"SN": "chr22", "LN": 51304566},
            {"SN": "chrX", "LN": 155270560},
            {"SN": "chrY", "LN": 59373566},
            {"SN": "chrM", "LN": 16571},
        ]

    @staticmethod
    def default_rg() -> Dict[str, str]:
        """Returns the default read group used by the SamBuilder, as a dictionary."""
        return {"ID": "1", "SM": "1_AAAAAA", "LB": "default", "PL": "ILLUMINA", "PU": "xxx.1"}

    def __init__(
        self,
        r1_len: Optional[int] = None,
        r2_len: Optional[int] = None,
        base_quality: int = 30,
        mapping_quality: int = 60,
        sd: Optional[List[Dict[str, Any]]] = None,
        rg: Optional[Dict[str, str]] = None,
        extra_header: Optional[Dict[str, Any]] = None,
        seed: int = 42,
    ) -> None:
        """Initializes a new SamBuilder for generating alignment records and SAM/BAM files.

        Args:
            r1_len: The length of R1s to create unless otherwise specified
            r2_len: The length of R2s to create unless otherwise specified
            base_quality: The base quality of bases to create unless otherwise specified
            sd: a sequence dictionary as a list of dicts; defaults to calling default_sd() if None
            rg: a single read group as a dict; defaults to calling default_sd() if None
            extra_header: a dictionary of extra values to add to the header, None otherwise.  See
                          `::class::~pysam.AlignmentHeader` for more details.
            seed: a seed value for random number/string generation
        """

        self.r1_len: int = r1_len if r1_len is not None else self.DEFAULT_R1_LENGTH
        self.r2_len: int = r2_len if r2_len is not None else self.DEFAULT_R2_LENGTH
        self.base_quality: int = base_quality
        self.mapping_quality: int = mapping_quality
        self._header: Dict[str, Any] = {
            "HD": {"VN": "1.5", "SO": "coordinate"},
            "SQ": (sd if sd is not None else SamBuilder.default_sd()),
            "RG": [(rg if rg is not None else SamBuilder.default_rg())],
        }
        if extra_header is not None:
            self._header = {**self._header, **extra_header}
        self._samheader = AlignmentHeader.from_dict(self._header)
        self._seq_lookup = dict([(s["SN"], s) for s in self._header["SQ"]])

        self._random: Random = Random(seed)
        self._records: List[AlignedSegment] = []
        self._counter: int = 0

    def _next_name(self) -> str:
        """Returns the next available query/template name."""
        n = self._counter
        self._counter += 1
        return f"q{n:>04}"

    def _bases(self, length: int) -> str:
        """Returns a random string of bases of the length requested."""
        return "".join(self._random.choices("ACGT", k=length))  # type: ignore

    def _new_rec(
        self,
        name: str,
        chrom: str,
        start: int,
        mapq: Optional[int],
        attrs: Optional[Dict[str, Any]],
    ) -> AlignedSegment:
        """Generates a new AlignedSegment.  Sets the segment up with the correct
        header and adds the RG attribute if not contained in attrs.

        Args:
            name: the name of the read/template
            chrom: the chromosome to which the read is mapped
            start: the start position of the read on the chromosome
            mapq: an optional mapping quality; use self.mapping_quality if None
            attrs: an optional dictionary of SAM attributes with two-char keys

        Returns:
            AlignedSegment: an aligned segment with name, chrom, pos, attributes the
                read group, and the unmapped flag all set appropriately.
        """
        if chrom is not sam.NO_REF_NAME and chrom not in self._seq_lookup:
            raise ValueError(f"{chrom} is not a valid chromosome name in this builder.")

        rec = AlignedSegment(header=self._samheader)
        rec.query_name = name
        rec.reference_name = chrom
        rec.reference_start = start
        rec.mapping_quality = mapq if mapq is not None else self.mapping_quality

        if chrom == sam.NO_REF_NAME or start == sam.NO_REF_POS:
            rec.is_unmapped = True
            rec.mapping_quality = 0

        attrs = attrs if attrs else dict()
        if "RG" not in attrs:
            attrs["RG"] = self.rg_id()
        rec.set_tags(list(attrs.items()))
        return rec

    def _set_flags(
        self,
        rec: pysam.AlignedSegment,
        read_num: Optional[int],
        strand: str,
        secondary: bool = False,
        supplementary: bool = False,
    ) -> None:
        """Appropriately sets most flag fields on the given read.

        Args:
            rec: the read to set the flags on
            read_num: Either None for an unpaired read, or 1 or 2
            strand: Either "+" or "-" to indicate strand of the read
        """
        rec.is_paired = read_num is not None
        rec.is_read1 = read_num == 1
        rec.is_read2 = read_num == 2
        rec.is_qcfail = False
        rec.is_duplicate = False
        rec.is_secondary = secondary
        rec.is_supplementary = supplementary
        if not rec.is_unmapped:
            rec.is_reverse = strand != "+"

    def _set_length_dependent_fields(
        self,
        rec: pysam.AlignedSegment,
        length: int,
        bases: Optional[str] = None,
        quals: Optional[List[int]] = None,
        cigar: Optional[str] = None,
    ) -> None:
        """Fills in bases, quals and cigar on a record.

        If any of bases, quals or cigar are defined, they must all have the same length/query
        length.  If none are defined then the length parameter is used.  Undefined values are
        synthesize at the inferred length.

        Args:
            rec: a SAM record
            length: the length to use if all of bases/quals/cigar are None
            bases: an optional string of bases for the read
            quals: an optional list of qualities for the read
            cigar: an optional cigar string for the read
        """

        # Do some validation to make sure all defined things have the same lengths
        lengths = set()
        if bases is not None:
            lengths.add(len(bases))
        if quals is not None:
            lengths.add(len(quals))
        if cigar is not None:
            cig = sam.Cigar.from_cigarstring(cigar)
            lengths.add(sum([elem.length_on_query for elem in cig.elements]))

        if not lengths:
            lengths.add(length)

        if len(lengths) != 1:
            raise ValueError("Provided bases/quals/cigar are not length compatible.")

        # Fill in the record, making any parts that were not defined as params
        length = lengths.pop()
        query_quals = array("B", quals if quals else [self.base_quality] * length)
        rec.query_sequence = bases if bases else self._bases(length)
        rec.query_qualities = query_quals
        if not rec.is_unmapped:
            rec.cigarstring = cigar if cigar else f"{length}M"

    def _set_mate_info(self, r1: pysam.AlignedSegment, r2: pysam.AlignedSegment) -> None:
        """Sets the mate information on a pair of sam records.

        Handles cases where both reads are mapped, one of the two reads is unmapped or both reads
        are unmapped.

        Args:
            r1: the first read in the pair
            r2: the sceond read in the pair
        """
        for rec in r1, r2:
            rec.template_length = 0
            rec.is_proper_pair = False

        if r1.is_unmapped and r2.is_unmapped:
            # If they're both unmapped just clean the records up
            for rec, other in [(r1, r2), (r2, r1)]:
                rec.reference_id = sam.NO_REF_INDEX
                rec.next_reference_id = sam.NO_REF_INDEX
                rec.reference_start = sam.NO_REF_POS
                rec.next_reference_start = sam.NO_REF_POS
                rec.is_unmapped = True
                rec.mate_is_unmapped = True
                rec.is_proper_pair = False
                rec.mate_is_reverse = other.is_reverse

        elif r1.is_unmapped or r2.is_unmapped:
            # If only one is mapped/unmapped copy over the relevant stuff
            (m, u) = (r1, r2) if r2.is_unmapped else (r2, r1)
            u.reference_id = m.reference_id
            u.reference_start = m.reference_start
            u.next_reference_id = m.reference_id
            u.next_reference_start = m.reference_start
            u.mate_is_reverse = m.is_reverse
            u.mate_is_unmapped = False
            u.set_tag("MC", m.cigarstring)

            m.next_reference_id = u.reference_id
            m.next_reference_start = u.reference_start
            m.mate_is_reverse = u.is_reverse
            m.mate_is_unmapped = True

        else:
            # Else they are both mapped
            for rec, other in [(r1, r2), (r2, r1)]:
                rec.next_reference_id = other.reference_id
                rec.next_reference_start = other.reference_start
                rec.mate_is_reverse = other.is_reverse
                rec.mate_is_unmapped = False
                rec.set_tag("MC", other.cigarstring)

            if r1.reference_id == r2.reference_id:
                r1p = r1.reference_end if r1.is_reverse else r1.reference_start
                r2p = r2.reference_end if r2.is_reverse else r2.reference_start
                r1.template_length = r2p - r1p
                r2.template_length = r1p - r2p

                # Arbitrarily set proper pair if the we have an FR pair with isize <= 1000
                if r1.is_reverse != r2.is_reverse and abs(r1.template_length) <= 1000:
                    fpos, rpos = (r2p, r1p) if r1.is_reverse else (r1p, r2p)
                    if fpos < rpos:
                        r1.is_proper_pair = True
                        r2.is_proper_pair = True

    def rg(self) -> Dict[str, Any]:
        """Returns the single read group that is defined in the header."""
        rgs = self._header["RG"]
        assert len(rgs) == 1, "Header did not contain exactly one read group!"
        return rgs[0]

    def rg_id(self) -> str:
        """Returns the ID of the single read group that is defined in the header."""
        return self.rg()["ID"]

    def add_pair(
        self,
        *,
        name: Optional[str] = None,
        bases1: Optional[str] = None,
        bases2: Optional[str] = None,
        quals1: Optional[List[int]] = None,
        quals2: Optional[List[int]] = None,
        chrom: str = sam.NO_REF_NAME,
        start1: int = sam.NO_REF_POS,
        start2: int = sam.NO_REF_POS,
        cigar1: Optional[str] = None,
        cigar2: Optional[str] = None,
        mapq1: Optional[int] = None,
        mapq2: Optional[int] = None,
        strand1: str = "+",
        strand2: str = "-",
        attrs: Optional[Dict[str, Any]] = None,
    ) -> Tuple[AlignedSegment, AlignedSegment]:
        """Generates a new pair of reads, adds them to the internal collection, and returns them.

        Most fields are optional.

        An unmapped pair can be created by calling the method with no parameters (specifically,
        not setting chrom, start1 or start2).  If either cigar is provided, it will be ignored.

        A pair with only one of the two reads mapped is created by setting e.g. chrom and start1.
        The values will be automaticaly transferred to the unmapped mate, and flags set correctly.

        A mapped pair is created by providing all three of chrom, start1 and start2.

        For a given read (i.e. R1 or R2) the length of the read is determined based on the presence
        or absence of bases, quals, and cigar.  If values are provided for one or more of these
        parameters, the lengths must match, and the length will be used to generate any
        unsupplied values.  If none of bases, quals, and cigar are provided, all three will be
        synthesized based on either the r1_len or r2_len stored on the class as appropriate.

        When synthesizing, bases are always a random sequence of bases, quals are all the default
        base quality (supplied when constructing a SamBuilder) and the cigar is always a single M
        operator of the read length.

        Args:
            name: The name of the template. If None is given a unique name will be auto-generated.
            bases1: The bases for R1. If None is given a random sequence is generated.
            bases2: The bases for R2. If None is given a random sequence is generated.
            quals1: The list of int qualities for R1. If None, the default base quality is used.
            quals2: The list of int qualities for R2. If None, the default base quality is used.
            chrom: The chromosome to which both reads are mapped. Defaults to the unmapped value.
            start1: The start position of R1. Defaults to the unmapped value.
            start2: The start position of R2. Defaults to the unmapped value.
            cigar1: The cigar string for R1. Defaults to None for unmapped reads, otherwise all M.
            cigar2: The cigar string for R2. Defaults to None for unmapped reads, otherwise all M.
            mapq1: Mapping quality for R1. Defaults to self.mapping_quality if None.
            mapq2: Mapping quality for R2. Defaults to self.mapping_quality if None.
            strand1: The strand for R1, either "+" or "-". Defaults to "+".
            strand2: The strand for R2, either "+" or "-". Defaults to "-".
            attrs: An optional dictionary of SAM attribute to place on both R1 and R2.

        Raises:
            ValueError: if either strand field is not "+" or "-"
            ValueError: if bases/quals/cigar are set in a way that is not self-consistent

        Returns:
            Tuple[AlignedSegment, AlignedSegment]: The pair of records created, R1 then R2.
        """

        if strand1 not in ["+", "-"]:
            raise ValueError(f"Invalid value for strand1: {strand1}")
        if strand2 not in ["+", "-"]:
            raise ValueError(f"Invalid value for strand2: {strand2}")

        name = name if name is not None else self._next_name()

        # Setup R1
        r1 = self._new_rec(name=name, chrom=chrom, start=start1, mapq=mapq1, attrs=attrs)
        self._set_flags(r1, read_num=1, strand=strand1)
        self._set_length_dependent_fields(
            rec=r1, length=self.r1_len, bases=bases1, quals=quals1, cigar=cigar1
        )

        # Setup R2
        r2 = self._new_rec(name=name, chrom=chrom, start=start2, mapq=mapq2, attrs=attrs)
        self._set_flags(r2, read_num=2, strand=strand2)
        self._set_length_dependent_fields(
            rec=r2, length=self.r2_len, bases=bases2, quals=quals2, cigar=cigar2
        )

        # Sync up mate info and we're done!
        self._set_mate_info(r1, r2)
        self._records.append(r1)
        self._records.append(r2)
        return r1, r2

    def add_single(
        self,
        *,
        name: Optional[str] = None,
        read_num: Optional[int] = None,
        bases: Optional[str] = None,
        quals: Optional[List[int]] = None,
        chrom: str = sam.NO_REF_NAME,
        start: int = sam.NO_REF_POS,
        cigar: Optional[str] = None,
        mapq: Optional[int] = None,
        strand: str = "+",
        secondary: bool = False,
        supplementary: bool = False,
        attrs: Optional[Dict[str, Any]] = None,
    ) -> AlignedSegment:
        """Generates a new single reads, adds them to the internal collection, and returns it.

        Most fields are optional.

        If `read_num` is None (the default) an unpaired read will be created.  If `read_num` is
        set to 1 or 2, the read will have it's paired flag set and read number flags set.

        An unmapped read can be created by calling the method with no parameters (specifically,
        not setting chrom, start1 or start2).  If cigar is provided, it will be ignored.

        A mapped read is created by providing chrom and start.

        The length of the read is determined based on the presence or absence of bases, quals,
        and cigar.  If values are provided for one or more of these parameters, the lengths must
        match, and the length will be used to generate any unsupplied values.  If none of bases,
        quals, and cigar are provided, all three will be synthesized based on either the r1_len
        or r2_len stored on the class as appropriate.

        When synthesizing, bases are always a random sequence of bases, quals are all the default
        base quality (supplied when constructing a SamBuilder) and the cigar is always a single M
        operator of the read length.

        Args:
            name: The name of the template. If None is given a unique name will be auto-generated.
            read_num: Either None, 1 for R1 or 2 for R2
            bases: The bases for the read. If None is given a random sequence is generated.
            quals: The list of qualities for the read. If None, the default base quality is used.
            chrom: The chromosome to which both reads are mapped. Defaults to the unmapped value.
            start: The start position of the read. Defaults to the unmapped value.
            cigar: The cigar string for R1. Defaults to None for unmapped reads, otherwise all M.
            mapq: Mapping quality for the read. Default to self.mapping_quality if not given.
            strand: The strand for R1, either "+" or "-". Defaults to "+".
            secondary: If true the read will be flagged as secondary
            supplementary: If true the read will be flagged as supplementary
            attrs: An optional dictionary of SAM attribute to place on both R1 and R2.

        Raises:
            ValueError: if strand field is not "+" or "-"
            ValueError: if read_num is not None, 1 or 2
            ValueError: if bases/quals/cigar are set in a way that is not self-consistent

        Returns:
            AlignedSegment: The record created
        """

        if strand not in ["+", "-"]:
            raise ValueError(f"Invalid value for strand1: {strand}")
        if read_num not in [None, 1, 2]:
            raise ValueError(f"Invalid value for read_num: {read_num}")

        name = name if name is not None else self._next_name()

        # Setup the read
        read_len = self.r1_len if read_num != 2 else self.r2_len
        rec = self._new_rec(name=name, chrom=chrom, start=start, mapq=mapq, attrs=attrs)
        self._set_flags(
            rec, read_num=read_num, strand=strand, secondary=secondary, supplementary=supplementary
        )
        self._set_length_dependent_fields(
            rec=rec, length=read_len, bases=bases, quals=quals, cigar=cigar
        )

        self._records.append(rec)
        return rec

    def to_path(
        self,
        path: Optional[Path] = None,
        index: bool = True,
        pred: Callable[[AlignedSegment], bool] = lambda r: True,
    ) -> Path:
        """Write the accumulated records to a file, sorts & indexes it, and returns the Path.
        If a path is provided, it will be written to, otherwise a temporary file is created
        and returned.

        Args:
            path: a path at which to write the file, otherwise a temp file is used.
            index: if True an index is generated, otherwise not.
            pred: optional predicate to specify which reads should be output

        Returns:
            Path: The path to the sorted (and possibly indexed) file.
        """

        if path is None:
            with NamedTemporaryFile(suffix=".bam", delete=False) as fp:
                path = Path(fp.name)

        with NamedTemporaryFile(suffix=".bam", delete=True) as fp:

            with sam.writer(
                fp.file, header=self._samheader, file_type=sam.SamFileType.BAM  # type: ignore
            ) as writer:
                for rec in self._records:
                    if pred(rec):
                        writer.write(rec)

            pysam.sort("-o", str(path), fp.name)  # type: ignore
            if index:
                pysam.index(str(path))  # type: ignore

        return path

    def __len__(self) -> int:
        """Returns the number of records accumulated so far."""
        return len(self._records)

    def to_unsorted_list(self) -> List[pysam.AlignedSegment]:
        """Returns the accumulated records in the order they were created."""
        return list(self._records)

    def to_sorted_list(self) -> List[pysam.AlignedSegment]:
        """Returns the accumulated records in coordinate order."""
        with NamedTemporaryFile(suffix=".bam", delete=True) as fp:
            filename = fp.name
            path = self.to_path(path=Path(filename), index=False)
            bam = sam.reader(path)
            return list(bam)
