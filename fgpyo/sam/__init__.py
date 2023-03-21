"""
Utility Classes and Methods for SAM/BAM
---------------------------------------

This module contains utility classes for working with SAM/BAM files and the data contained
within them.  This includes i) utilities for opening SAM/BAM files for reading and writing,
ii) functions for manipulating supplementary alignments, iii) classes and functions for
maniuplating CIGAR strings, and iv) a class for building sam records and files for testing.

Motivation for Reader and Writer methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following are the reasons for choosing to implement methods to open a SAM/BAM file for
reading and writing, rather than relying on :class:`pysam.AlignmentFile` directly:

1. Provides a centralized place for the implementation of opening a SAM/BAM for reading and
   writing.  This is useful if any additional parameters are added, or changes to standards or
   defaults are made.
2. Makes the requirement to provide a header when opening a file for writing more explicit.
3. Adds support for :class:`~pathlib.Path`.
4. Remove the reliance on specifying the mode correctly, including specifying the file type (i.e.
   SAM, BAM, or CRAM), as well as additional options (ex. compression level).  This makes the
   code more explicit and easier to read.
5. An explicit check is performed to ensure the file type is specified when writing using a
   file-like object rather than a path to a file.

Examples of Opening a SAM/BAM for Reading or Writing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Opening a SAM/BAM file for reading, auto-recognizing the file-type by the file extension.  See
:class:`~fgpyo.sam.SamFileType` for the supported file types.

.. code-block:: python

    >>> from fgpyo.sam import reader
    >>> with reader("/path/to/sample.sam") as fh:
    ...     for record in fh:
    ...         print(record.name)  # do something
    >>> with reader("/path/to/sample.bam") as fh:
    ...     for record in fh:
    ...         print(record.name)  # do something

Opening a SAM/BAM file for reading, explicitly passing the file type.

    >>> from fgpyo.sam import SamFileType
    >>> with reader(path="/path/to/sample.ext1", file_type=SamFileType.SAM) as fh:
    ...     for record in fh:
    ...         print(record.name)  # do something
    >>> with reader(path="/path/to/sample.ext2", file_type=SamFileType.BAM) as fh:
    ...     for record in fh:
    ...         print(record.name)  # do something

Opening a SAM/BAM file for reading, using an existing file-like object

    >>> with open("/path/to/sample.sam", "rb") as file_object:
    ...     with reader(path=file_object, file_type=SamFileType.BAM) as fh:
    ...         for record in fh:
    ...             print(record.name)  # do something

Opening a SAM/BAM file for writing follows similar to the :func:`~fgpyo.sam.reader` method,
but the SAM file header object is required.

    >>> from fgpyo.sam import writer
    >>> header: Dict[str, Any] = {
    ...     "HD": {"VN": "1.5", "SO": "coordinate"},
    ...     "RG": [{"ID": "1", "SM": "1_AAAAAA", "LB": "lib", "PL": "ILLUMINA", "PU": "xxx.1"}],
    ...     "SQ":  [
    ...         {"SN": "chr1", "LN": 249250621},
    ...         {"SN": "chr2", "LN": 243199373}
    ...     ]
    ... }
    >>> with writer(path="/path/to/sample.bam", header=header) as fh:
    ...     pass  # do something

Examples of Manipulating Cigars
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Creating a :class:`~fgpyo.sam.Cigar` from a :class:`pysam.AlignedSegment`.

    >>> from fgpyo.sam import Cigar
    >>> with reader("/path/to/sample.sam") as fh:
    ...     record = next(fh)
    ...     cigar = Cigar.from_cigartuples(record.cigartuples)
    ...     print(str(cigar))
    50M2D5M10S

Creating a :class:`~fgpyo.sam.Cigar` from a :class:`str`.

    >>> cigar = Cigar.from_cigarstring("50M2D5M10S")
    >>> print(str(cigar))
    50M2D5M10S

If the cigar string is invalid, the exception message will show you the problem character(s) in
square brackets.

    >>> cigar = Cigar.from_cigarstring("10M5U")
    ... CigarException("Malformed cigar: 10M5[U]")

The cigar contains a tuple of :class:`~fgpyo.sam.CigarElement`s.  Each element contains the
cigar operator (:class:`~fgpyo.sam.CigarOp`) and associated operator length.  A number of
useful methods are part of both classes.

The number of bases aligned on the query (i.e. the number of bases consumed by the cigar from
the query):

    >>> cigar = Cigar.from_cigarstring("50M2D5M2I10S")
    >>> [e.length_on_query for e in cigar.elements]
    [50, 0, 5, 2, 10]
    >>> [e.length_on_target for e in cigar.elements]
    [50, 2, 5, 0, 0]
    >>> [e.operator.is_indel for e in cigar.elements]
    [False, True, False, True, False]


Examples of parsing the SA tag and individual supplementary alignments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

   >>> from fgpyo.sam import SupplementaryAlignment
   >>> sup = SupplementaryAlignment.parse("chr1,123,+,50S100M,60,0")
   >>> sup.reference_name
   'chr1
   >>> sup.nm
   0
   >>> from typing import List
   >>> sa_tag = "chr1,123,+,50S100M,60,0;chr2,456,-,75S75M,60,1"
   >>> sups: List[SupplementaryAlignment] = SupplementaryAlignment.parse_sa_tag(tag=sa_tag)
   >>> len(sups)
   2
   >>> [str(sup.cigar) for sup in sups]
   ['50S100M', '75S75M']

Module Contents
~~~~~~~~~~~~~~~
The module contains the following public classes:
    - :class:`~fgpyo.sam.SupplementaryAlignment` -- Stores a supplementary alignment record
        produced by BWA and stored in the SA SAM tag.
    - :class:`~fgpyo.sam.SamFileType` -- Enumeration of valid SAM/BAM/CRAM file types.
    - :class:`~fgpyo.sam.CigarOp` -- Enumeration of operators that can appear in a Cigar string.
    - :class:`~fgpyo.sam.CigarElement` -- Class representing an element in a Cigar string.
    - :class:`~fgpyo.sam.CigarParsingException` -- The exception raised specific to parsing a
        cigar
    - :class:`~fgpyo.sam.Cigar` -- Class representing a cigar string.
    - :class:`~fgpyo.sam.ReadEditInfo` -- Class describing how a read differs from the reference

The module contains the following methods:

    - :func:`~fgpyo.sam.reader` -- opens a SAM/BAM/CRAM file for reading.
    - :func:`~fgpyo.sam.writer` -- opens a SAM/BAM/CRAM file for writing
    - :func:`~fgpyo.sam.calc_edit_info` -- calculates how a read differs from the reference
"""

import enum
import io
from pathlib import Path
from typing import IO
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import attr
import pysam
from pysam import AlignedSegment
from pysam import AlignmentFile as SamFile
from pysam import AlignmentHeader as SamHeader

from fgpyo.collections import PeekableIterator

SamPath = Union[IO[Any], Path, str]
"""The valid base classes for opening a SAM/BAM/CRAM file."""

NO_REF_INDEX: int = -1
"""The reference index to use to indicate no reference in SAM/BAM."""

NO_REF_NAME: str = "*"
"""The reference name to use to indicate no reference in SAM/BAM."""

NO_REF_POS: int = -1
"""The reference position to use to indicate no position in SAM/BAM."""

_IOClasses = (io.TextIOBase, io.BufferedIOBase, io.RawIOBase, io.IOBase)
"""The classes that should be treated as file-like classes"""


@enum.unique
class SamFileType(enum.Enum):
    """Enumeration of valid SAM/BAM/CRAM file types.

    Attributes:
        mode (str): The additional mode character to add when opening this file type.
        ext (str): The standard file extension for this file type.
    """

    def __init__(self, mode: str, ext: str) -> None:
        self.mode = mode
        self.extension = ext

    SAM = ("", ".sam")
    BAM = ("b", ".bam")
    CRAM = ("c", ".cram")

    @classmethod
    def from_path(cls, path: Union[Path, str]) -> "SamFileType":
        """Infers the file type based on the file extension.

        Args:
            path: the path to the SAM/BAM/CRAM to read or write.
        """
        ext = Path(path).suffix
        try:
            return next(iter([tpe for tpe in SamFileType if tpe.extension == ext]))
        except StopIteration:
            raise ValueError(f"Could not infer file type from {path}")


def _pysam_open(
    path: SamPath, open_for_reading: bool, file_type: Optional[SamFileType] = None, **kwargs: Any
) -> SamFile:
    """Opens a SAM/BAM/CRAM for reading or writing.

    Args:
        path: a file handle or path to the SAM/BAM/CRAM to read or write.
        open_for_reading: True to open for reading, false otherwise.
        file_type: the file type to assume when opening the file.  If None, then the file type
            will be auto-detected for reading and must be a path-like object for writing.
        kwargs: any keyword arguments to be passed to
        :class:`~pysam.AlignmentFile`; may not include "mode".
    """

    if isinstance(path, (str, Path)):  # type: ignore
        file_type = file_type or SamFileType.from_path(path)
        path = str(path)
    elif not isinstance(path, _IOClasses):  # type: ignore
        open_type = "reading" if open_for_reading else "writing"
        raise TypeError(f"Cannot open '{type(path)}' for {open_type}.")

    if file_type is None and not open_for_reading:
        raise ValueError("file_type must be given when writing to a file-like object")

    # file_type must be set when writing, so if file_type is None, then we must be opening it
    # for reading.  Hence, only set mode in kwargs to pysam when file_type is set and when
    # writing since we can let pysam auto-recognize the file type when reading.  See discussion:
    # https://github.com/pysam-developers/pysam/issues/655
    if file_type is not None:
        kwargs["mode"] = "r" if open_for_reading else "w" + file_type.mode
    else:
        assert open_for_reading, "Bug: file_type was None but open_for_reading was False"

    # Open it!
    return pysam.AlignmentFile(path, **kwargs)


def reader(path: SamPath, file_type: Optional[SamFileType] = None) -> SamFile:
    """Opens a SAM/BAM/CRAM for reading.

    Args:
        path: a file handle or path to the SAM/BAM/CRAM to read or write.
        file_type: the file type to assume when opening the file.  If None, then the file
            type will be auto-detected.
    """
    return _pysam_open(path=path, open_for_reading=True, file_type=file_type)


def writer(
    path: SamPath,
    header: Union[str, Dict[str, Any], SamHeader],
    file_type: Optional[SamFileType] = None,
) -> SamFile:
    """Opens a SAM/BAM/CRAM for writing.

    Args:
        path: a file handle or path to the SAM/BAM/CRAM to read or write.
        header: Either a string to use for the header or a multi-level dictionary.  The
            multi-level dictionary should be given as follows.  The first level are the four
            types (‘HD’, ‘SQ’, ...). The second level are a list of lines, with each line being
            a list of tag-value pairs. The header is constructed first from all the defined
            fields, followed by user tags in alphabetical order.
        file_type: the file type to assume when opening the file.  If None, then the
            filetype will be auto-detected and must be a path-like object.
    """
    # Set the header for pysam's AlignmentFile
    key = "text" if isinstance(header, str) else "header"
    kwargs = {key: header}

    return _pysam_open(path=path, open_for_reading=False, file_type=file_type, **kwargs)


class _CigarOpUtil:
    """Some useful constants to speed up methods on CigarOp"""

    """A dictionary from the cigar op code to the cigar op char.

    This is to speed up the translation of cigar op code to CigarOp in CigarOp, so needs to be
    declared beforehand.
    """
    CODE_TO_CHARACTER: Dict[int, str] = {
        0: "M",
        1: "I",
        2: "D",
        3: "N",
        4: "S",
        5: "H",
        6: "P",
        7: "EQ",
        8: "X",
    }


@enum.unique
class CigarOp(enum.Enum):
    """Enumeration of operators that can appear in a Cigar string.

    Attributes:
        code (int): The :py:mod:`~pysam` cigar operator code.
        character (int): The single character cigar operator.
        consumes_query (bool): True if this operator consumes query bases, False otherwise.
        consumes_target (bool): True if this operator consumes target bases, False otherwise.
    """

    M = (0, "M", True, True)  #: Match or Mismatch the reference
    I = (1, "I", True, False)  #: Insertion versus the reference  # noqa: E741
    D = (2, "D", False, True)  #: Deletion versus the reference
    N = (3, "N", False, True)  #: Skipped region from the reference
    S = (4, "S", True, False)  #: Soft clip
    H = (5, "H", False, False)  #: Hard clip
    P = (6, "P", False, False)  #: Padding
    EQ = (7, "=", True, True)  #: Matches the reference
    X = (8, "X", True, True)  #: Mismatches the reference

    def __init__(
        self, code: int, character: str, consumes_query: bool, consumes_reference: bool
    ) -> None:
        self.code = code
        self.character = character
        self.consumes_query = consumes_query
        self.consumes_reference = consumes_reference

    @staticmethod
    def from_character(character: str) -> "CigarOp":
        """Returns the operator from the single character."""
        if CigarOp.EQ.character == character:
            return CigarOp.EQ
        else:
            return CigarOp[character]

    @staticmethod
    def from_code(code: int) -> "CigarOp":
        """Returns the operator from the given operator code.

        Note: this is mainly used to get the operator from :py:mod:`~pysam`.
        """
        return CigarOp[_CigarOpUtil.CODE_TO_CHARACTER[code]]

    @property
    def is_indel(self) -> bool:
        """Returns true if the operator is an indel, false otherwise."""
        return self == CigarOp.I or self == CigarOp.D


@attr.s(frozen=True, slots=True)
class CigarElement:
    """Represents an element in a Cigar

    Attributes:
        - length (int): the length of the element
        - operator (CigarOp): the operator of the element
    """

    length: int = attr.ib()
    operator: CigarOp = attr.ib()

    @length.validator
    def _validate_length(self, attribute: Any, value: int) -> None:
        """Validates the length attribute is greater than zero."""
        if value <= 0:
            raise ValueError(f"Cigar element must have a length > 0, found {value}")

    @property
    def length_on_query(self) -> int:
        """Returns the length of the element on the query sequence."""
        return self.length if self.operator.consumes_query else 0

    @property
    def length_on_target(self) -> int:
        """Returns the length of the element on the target (often reference) sequence."""
        return self.length if self.operator.consumes_reference else 0

    def __str__(self) -> str:
        return f"{self.length}{self.operator.character}"


class CigarParsingException(Exception):
    """The exception raised specific to parsing a cigar."""

    pass


@attr.s(frozen=True, slots=True)
class Cigar:
    """Class representing a cigar string.

    Attributes:
        - elements (Tuple[CigarElement, ...]): zero or more cigar elements
    """

    elements: Tuple[CigarElement, ...] = attr.ib(default=())

    @classmethod
    def from_cigartuples(cls, cigartuples: Optional[List[Tuple[int, int]]]) -> "Cigar":
        """Returns a Cigar from a list of tuples returned by pysam.

        Each tuple denotes the operation and length.  See
        :class:`~fgpyo.sam.CigarOp` for more information on the
        various operators.  If None is given, returns an empty Cigar.
        """
        if cigartuples is None or cigartuples == []:
            return Cigar()
        try:
            elements = []
            for code, length in cigartuples:
                operator = CigarOp.from_code(code)
                elements.append(CigarElement(length, operator))
            return Cigar(tuple(elements))
        except Exception as ex:
            raise CigarParsingException(f"Malformed cigar tuples: {cigartuples}") from ex

    @classmethod
    def _pretty_cigarstring_exception(cls, cigarstring: str, index: int) -> CigarParsingException:
        """Raises an exception highlighting the malformed character"""
        prefix = cigarstring[:index]
        character = cigarstring[index] if index < len(cigarstring) else ""
        suffix = cigarstring[index + 1 :]
        pretty_cigarstring = f"{prefix}[{character}]{suffix}"
        message = f"Malformed cigar: {pretty_cigarstring}"
        return CigarParsingException(message)

    @classmethod
    def from_cigarstring(cls, cigarstring: str) -> "Cigar":
        """Constructs a Cigar from a string returned by pysam.

        If "*" is given, returns an empty Cigar.
        """
        if cigarstring == "*":
            return Cigar()

        cigarstring_length = len(cigarstring)
        if cigarstring_length == 0:
            raise CigarParsingException("Cigar string was empty")

        elements = []
        i = 0
        while i < cigarstring_length:
            if not cigarstring[i].isdigit():
                raise cls._pretty_cigarstring_exception(cigarstring, i)  # type: ignore
            length = int(cigarstring[i])
            i += 1
            while i < cigarstring_length and cigarstring[i].isdigit():
                length = (length * 10) + int(cigarstring[i])
                i += 1
            if i == cigarstring_length:
                raise cls._pretty_cigarstring_exception(cigarstring, i)  # type: ignore
            try:
                operator = CigarOp.from_character(cigarstring[i])
                elements.append(CigarElement(length, operator))
            except KeyError as ex:
                # cigar operator was not valid
                raise cls._pretty_cigarstring_exception(cigarstring, i) from ex  # type: ignore
            except IndexError as ex:
                # missing cigar operator (i == len(cigarstring))
                raise cls._pretty_cigarstring_exception(cigarstring, i) from ex  # type: ignore
            i += 1
        return Cigar(tuple(elements))

    def __str__(self) -> str:
        if self.elements:
            return "".join([str(e) for e in self.elements])
        else:
            return "*"

    def reversed(self) -> "Cigar":
        """Returns a copy of the Cigar with the elements in reverse order."""
        return Cigar(tuple(reversed(self.elements)))

    def length_on_query(self) -> int:
        """Returns the length of the alignment on the query sequence."""
        return sum([elem.length_on_query for elem in self.elements])

    def length_on_target(self) -> int:
        """Returns the length of the alignment on the target sequence."""
        return sum([elem.length_on_target for elem in self.elements])


@attr.s(auto_attribs=True, frozen=True)
class SupplementaryAlignment:
    """Stores a supplementary alignment record produced by BWA and stored in the SA SAM tag.

    Attributes:
        reference_name: the name of the reference (i.e. contig, chromosome) aligned to
        start: the 0-based start position of the alignment
        is_forward: true if the alignment is in the forward strand, false otherwise
        cigar: the cigar for the alignment
        mapq: the mapping quality
        nm: the number of edits
    """

    reference_name: str = attr.ib()
    start: int = attr.ib()
    is_forward: bool = attr.ib()
    cigar: Cigar = attr.ib()
    mapq: int = attr.ib()
    nm: int = attr.ib()

    def __str__(self) -> str:
        return ",".join(
            str(item)
            for item in (
                self.reference_name,
                self.start + 1,
                "+" if self.is_forward else "-",
                self.cigar,
                self.mapq,
                self.nm,
            )
        )

    @staticmethod
    def parse(string: str) -> "SupplementaryAlignment":
        """Returns a supplementary alignment parsed from the given string.  The various fields
        should be comma-delimited (ex. `chr1,123,-,100M50S,60,4`)
        """
        fields = string.split(",")
        return SupplementaryAlignment(
            reference_name=fields[0],
            start=int(fields[1]) - 1,
            is_forward=fields[2] == "+",
            cigar=Cigar.from_cigarstring(fields[3]),
            mapq=int(fields[4]),
            nm=int(fields[5]),
        )

    @staticmethod
    def parse_sa_tag(tag: str) -> List["SupplementaryAlignment"]:
        """Parses an SA tag of supplementary alignments from a BAM file. If the tag is empty
        or contains just a single semi-colon then an empty list will be returned.  Otherwise
        a list containing a SupplementaryAlignment per ;-separated value in the tag will
        be returned.
        """
        return [SupplementaryAlignment.parse(a) for a in tag.split(";") if len(a) > 0]


def isize(r1: AlignedSegment, r2: AlignedSegment) -> int:
    """Computes the insert size for a pair of records."""
    if r1.is_unmapped or r2.is_unmapped or r1.reference_id != r2.reference_id:
        return 0
    else:
        r1_pos = r1.reference_end if r1.is_reverse else r1.reference_start
        r2_pos = r2.reference_end if r2.is_reverse else r2.reference_start
        return r2_pos - r1_pos


def set_pair_info(r1: AlignedSegment, r2: AlignedSegment, proper_pair: bool = True) -> None:
    """Resets mate pair information between reads in a pair. Requires that both r1
    and r2 are mapped.  Can be handed reads that already have pairing flags setup or
    independent R1 and R2 records that are currently flagged as SE reads.

    Args:
        r1: read 1
        r2: read 2 with the same queryname as r1
    """
    assert not r1.is_unmapped, f"Cannot process unmapped mate {r1.query_name}/1"
    assert not r2.is_unmapped, f"Cannot process unmapped mate {r2.query_name}/2"
    assert r1.query_name == r2.query_name, "Attempting to pair reads with different qnames."

    for r in [r1, r2]:
        r.is_paired = True
        r.is_proper_pair = proper_pair

    r1.is_read1 = True
    r1.is_read2 = False
    r2.is_read2 = True
    r2.is_read1 = False

    for src, dest in [(r1, r2), (r2, r1)]:
        dest.next_reference_id = src.reference_id
        dest.next_reference_start = src.reference_start
        dest.mate_is_reverse = src.is_reverse
        dest.mate_is_unmapped = False
        dest.set_tag("MC", src.cigarstring)

    insert_size = isize(r1, r2)
    r1.template_length = insert_size
    r2.template_length = -insert_size


@attr.s(auto_attribs=True, frozen=True)
class ReadEditInfo:
    """
    Counts various stats about how a read compares to a reference sequence.

    Attributes:
        matches: the number of bases in the read that match the reference
        mismatches: the number of mismatches between the read sequence and the reference sequence
          as dictated by the alignment.  Like as defined for the SAM NM tag computation, any base
          except A/C/G/T in the read is considered a mismatch.
        insertions: the number of insertions in the read vs. the reference.  I.e. the number of I
          operators in the CIGAR string.
        inserted_bases: the total number of bases contained within insertions in the read
        deletions: the number of deletions in the read vs. the reference.  I.e. the number of D
          operators in the CIGAT string.
        deleted_bases: the total number of that are deleted within the alignment (i.e. bases in
          the reference but not in the read).
        nm: the computed value of the SAM NM tag, calculated as mismatches + inserted_bases +
          deleted_bases
    """

    matches: int
    mismatches: int
    insertions: int
    inserted_bases: int
    deletions: int
    deleted_bases: int
    nm: int


def calculate_edit_info(
    rec: AlignedSegment, reference_sequence: str, reference_offset: Optional[int] = None
) -> ReadEditInfo:
    """
    Constructs a `ReadEditInfo` instance giving summary stats about how the read aligns to the
    reference.  Computes the number of mismatches, indels, indel bases and the SAM NM tag.
    The read must be aligned.

    Args:
        rec: the read/record for which to calculate values
        reference_sequence: the reference sequence (or fragment thereof) that the read is
          aligned to
        reference_offset: if provided, assume that reference_sequence[reference_offset] is the
          first base aligned to in reference_sequence, otherwise use r.reference_start

    Returns:
        a ReadEditInfo with information about how the read differs from the reference
    """
    assert not rec.is_unmapped, f"Cannot calculate edit info for unmapped read: {rec}"

    query_offset = 0
    target_offset = reference_offset if reference_offset is not None else rec.reference_start
    cigar = Cigar.from_cigartuples(rec.cigartuples)

    matches, mms, insertions, ins_bases, deletions, del_bases = 0, 0, 0, 0, 0, 0
    ok_bases = {"A", "C", "G", "T"}

    for elem in cigar.elements:
        op = elem.operator

        if op == CigarOp.I:
            insertions += 1
            ins_bases += elem.length
        elif op == CigarOp.D:
            deletions += 1
            del_bases += elem.length
        elif op == CigarOp.M or op == CigarOp.X or op == CigarOp.EQ:
            for i in range(0, elem.length):
                q = rec.query_sequence[query_offset + i].upper()
                t = reference_sequence[target_offset + i].upper()
                if q != t or q not in ok_bases:
                    mms += 1
                else:
                    matches += 1

        query_offset += elem.length_on_query
        target_offset += elem.length_on_target

    return ReadEditInfo(
        matches=matches,
        mismatches=mms,
        insertions=insertions,
        inserted_bases=ins_bases,
        deletions=deletions,
        deleted_bases=del_bases,
        nm=mms + ins_bases + del_bases,
    )


@attr.s(auto_attribs=True, frozen=True)
class Template:
    """A container for alignment records corresponding to a single sequenced template
    or insert.

    It is strongly preferred that new Template instances be created with `Template.build()`
    which will ensure that reads are stored in the correct Template property, and run basic
    validations of the Template by default.  If constructing Template instances by construction
    users are encouraged to use the validate method post-construction.

    Attributes:
        name: the name of the template/query
        r1: Primary alignment for read 1, or None if there is none
        r2: Primary alignment for read 2, or None if there is none
        r1_supplementals: Supplementary alignments for read 1
        r2_supplementals: Supplementary alignments for read 2
        r1_secondaries: Secondary (non-primary) alignments for read 1
        r2_secondaries: Secondary (non-primary) alignments for read 2
    """

    name: str
    r1: Optional[AlignedSegment]
    r2: Optional[AlignedSegment]
    r1_supplementals: List[AlignedSegment]
    r2_supplementals: List[AlignedSegment]
    r1_secondaries: List[AlignedSegment]
    r2_secondaries: List[AlignedSegment]

    @staticmethod
    def iterator(alns: Iterator[AlignedSegment]) -> Iterator["Template"]:
        """Returns an iterator over templates. Assumes the input iterable is queryname grouped,
        and gathers consecutive runs of records sharing a common query name into templates."""
        return TemplateIterator(alns)

    @staticmethod
    def build(recs: Iterable[AlignedSegment], validate: bool = True) -> "Template":
        """Build a template from a set of records all with the same queryname."""
        name = None
        r1 = None
        r2 = None
        r1_supplementals: List[AlignedSegment] = []
        r2_supplementals: List[AlignedSegment] = []
        r1_secondaries: List[AlignedSegment] = []
        r2_secondaries: List[AlignedSegment] = []

        for rec in recs:
            if name is None:
                name = rec.query_name

            is_r1 = not rec.is_paired or rec.is_read1

            if not rec.is_supplementary and not rec.is_secondary:
                if is_r1:
                    assert r1 is None, f"Multiple R1 primary reads found in {recs}"
                    r1 = rec
                else:
                    assert r2 is None, f"Multiple R2 primary reads found in {recs}"
                    r2 = rec
            elif rec.is_supplementary:
                if is_r1:
                    r1_supplementals.append(rec)
                else:
                    r2_supplementals.append(rec)
            if rec.is_secondary:
                if is_r1:
                    r1_secondaries.append(rec)
                else:
                    r2_secondaries.append(rec)

        assert name is not None, "Cannot construct a template from zero records."

        template = Template(
            name=name,
            r1=r1,
            r2=r2,
            r1_supplementals=r1_supplementals,
            r2_supplementals=r2_supplementals,
            r1_secondaries=r1_secondaries,
            r2_secondaries=r2_secondaries,
        )

        if validate:
            template.validate()

        return template

    def validate(self) -> None:
        """Performs sanity checks that all the records in the Template are as expected."""
        for rec in self.all_recs():
            assert rec.query_name == self.name, f"Name error {self.name} vs. {rec.query_name}"

        if self.r1 is not None:
            assert self.r1.is_read1 or not self.r1.is_paired, "R1 not flagged as R1 or unpaired"
            assert not self.r1.is_supplementary, "R1 primary flagged as supplementary"
            assert not self.r1.is_secondary, "R1 primary flagged as secondary"

        if self.r2 is not None:
            assert self.r2.is_read2, "R2 not flagged as R2"
            assert not self.r2.is_supplementary, "R2 primary flagged as supplementary"
            assert not self.r2.is_secondary, "R2 primary flagged as secondary"

        for rec in self.r1_secondaries:
            assert rec.is_read1 or not rec.is_paired, "R1 secondary not flagged as R1 or unpaired"
            assert rec.is_secondary, "R1 secondary not flagged as secondary"

        for rec in self.r1_supplementals:
            assert rec.is_read1 or not rec.is_paired, "R1 supp. not flagged as R1 or unpaired"
            assert rec.is_supplementary, "R1 supp. not flagged as supplementary"

        for rec in self.r2_secondaries:
            assert rec.is_read2, "R2 secondary not flagged as R2"
            assert rec.is_secondary, "R2 secondary not flagged as secondary"

        for rec in self.r2_supplementals:
            assert rec.is_read2, "R2 supp. not flagged as R2"
            assert rec.is_supplementary, "R2 supp. not flagged as supplementary"

    def primary_recs(self) -> Iterator[AlignedSegment]:
        """Returns a list with all the primary records for the template."""
        return (r for r in (self.r1, self.r2) if r is not None)

    def all_recs(self) -> Iterator[AlignedSegment]:
        """Returns a list with all the records for the template."""
        for rec in self.primary_recs():
            yield rec

        for recs in (
            self.r1_supplementals,
            self.r1_secondaries,
            self.r2_supplementals,
            self.r2_secondaries,
        ):
            for rec in recs:
                yield rec


class TemplateIterator(Iterator[Template]):
    """
    An iterator that converts an iterator over query-grouped reads into an iterator
    over templates.
    """

    def __init__(self, iterator: Iterator[AlignedSegment]) -> None:
        self._iter = PeekableIterator(iterator)

    def __iter__(self) -> Iterator[Template]:
        return self

    def __next__(self) -> Template:
        name = self._iter.peek().query_name
        recs = self._iter.takewhile(lambda r: r.query_name == name)
        return Template.build(recs, validate=False)
