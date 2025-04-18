"""
# Utility Classes and Methods for SAM/BAM

This module contains utility classes for working with SAM/BAM files and the data contained
within them.  This includes i) utilities for opening SAM/BAM files for reading and writing,
ii) functions for manipulating supplementary alignments, iii) classes and functions for
maniuplating CIGAR strings, and iv) a class for building sam records and files for testing.

## Motivation for Reader and Writer methods

The following are the reasons for choosing to implement methods to open a SAM/BAM file for
reading and writing, rather than relying on `pysam.AlignmentFile` directly:

1. Provides a centralized place for the implementation of opening a SAM/BAM for reading and
   writing.  This is useful if any additional parameters are added, or changes to standards or
   defaults are made.
2. Makes the requirement to provide a header when opening a file for writing more explicit.
3. Adds support for `pathlib.Path`.
4. Remove the reliance on specifying the mode correctly, including specifying the file type (i.e.
   SAM, BAM, or CRAM), as well as additional options (ex. compression level).  This makes the
   code more explicit and easier to read.
5. An explicit check is performed to ensure the file type is specified when writing using a
   file-like object rather than a path to a file.

## Examples of Opening a SAM/BAM for Reading or Writing

Opening a SAM/BAM file for reading, auto-recognizing the file-type by the file extension.  See
[`SamFileType()`][fgpyo.sam.SamFileType] for the supported file types.

```python
    >>> from fgpyo.sam import reader
    >>> with reader("/path/to/sample.sam") as fh:
    ...     for record in fh:
    ...         print(record.name)  # do something
    >>> with reader("/path/to/sample.bam") as fh:
    ...     for record in fh:
    ...         print(record.name)  # do something
```

Opening a SAM/BAM file for reading, explicitly passing the file type.

```python
    >>> from fgpyo.sam import SamFileType
    >>> with reader(path="/path/to/sample.ext1", file_type=SamFileType.SAM) as fh:
    ...     for record in fh:
    ...         print(record.name)  # do something
    >>> with reader(path="/path/to/sample.ext2", file_type=SamFileType.BAM) as fh:
    ...     for record in fh:
    ...         print(record.name)  # do something
```

Opening a SAM/BAM file for reading, using an existing file-like object

```python
    >>> with open("/path/to/sample.sam", "rb") as file_object:
    ...     with reader(path=file_object, file_type=SamFileType.BAM) as fh:
    ...         for record in fh:
    ...             print(record.name)  # do something
```

Opening a SAM/BAM file for writing follows similar to the [`reader()`][fgpyo.sam.reader]
method, but the SAM file header object is required.

```python
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
```

## Examples of Manipulating Cigars

Creating a [`Cigar` from a `pysam.AlignedSegment`][fgpyo.sam.Cigar].

```python
    >>> from fgpyo.sam import Cigar
    >>> with reader("/path/to/sample.sam") as fh:
    ...     record = next(fh)
    ...     cigar = Cigar.from_cigartuples(record.cigartuples)
    ...     print(str(cigar))
    50M2D5M10S
```

Creating a [`Cigar` from a `str()`][fgpyo.sam.Cigar].

```python
    >>> cigar = Cigar.from_cigarstring("50M2D5M10S")
    >>> print(str(cigar))
    50M2D5M10S
```

If the cigar string is invalid, the exception message will show you the problem character(s) in
square brackets.

```python
    >>> cigar = Cigar.from_cigarstring("10M5U")
    ... CigarException("Malformed cigar: 10M5[U]")
```

The cigar contains a tuple of [`CigarElement()`][fgpyo.sam.CigarElement]s.  Each element
contains the cigar operator ([`CigarOp()`][fgpyo.sam.CigarOp]) and associated operator
length.  A number of useful methods are part of both classes.

The number of bases aligned on the query (i.e. the number of bases consumed by the cigar from
the query):

```python
    >>> cigar = Cigar.from_cigarstring("50M2D5M2I10S")
    >>> [e.length_on_query for e in cigar.elements]
    [50, 0, 5, 2, 10]
    >>> [e.length_on_target for e in cigar.elements]
    [50, 2, 5, 0, 0]
    >>> [e.operator.is_indel for e in cigar.elements]
    [False, True, False, True, False]
```

Any particular tuple can be accessed directly with its index (and works with negative indexes
and slices):

    >>> cigar = Cigar.from_cigarstring("50M2D5M2I10S")
    >>> cigar[0].length
    50
    >>> cigar[1].operator
    <CigarOp.D: (2, 'D', False, True)>
    >>> cigar[-1].operator
    <CigarOp.S: (4, 'S', True, False)>
    >>> tuple(x.operator.character for x in cigar[1:3])
    ('D','M')
    >>> tuple(x.operator.character for x in cigar[-2:])
    ('I', 'S')

## Examples of parsing the SA tag and individual supplementary alignments

```python
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
```
"""

import enum
import io
import sys
from array import array
from collections.abc import Collection
from itertools import chain
from pathlib import Path
from typing import IO
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from typing import cast

import attr
import pysam
from pysam import AlignedSegment
from pysam import AlignmentFile as SamFile
from pysam import AlignmentHeader as SamHeader
from pysam import qualitystring_to_array

if sys.version_info[:2] > (3, 10):
    from typing import Self
else:
    from typing_extensions import Self

if sys.version_info[:2] > (3, 12):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

import fgpyo.io
from fgpyo.collections import PeekableIterator

SamPath = Union[IO[Any], Path, str]
"""The valid base classes for opening a SAM/BAM/CRAM file."""

NO_REF_INDEX: int = -1
"""The reference index to use to indicate no reference in SAM/BAM."""

STRING_PLACEHOLDER: str = "*"
"""The value to use when a string field's information is unavailable."""

NO_REF_NAME: str = STRING_PLACEHOLDER
"""The reference name to use to indicate no reference in SAM/BAM."""

NO_REF_POS: int = -1
"""The reference position to use to indicate no position in SAM/BAM."""

NO_QUERY_QUALITIES: array = qualitystring_to_array(STRING_PLACEHOLDER)
"""The quality array corresponding to an unavailable query quality string ("*")."""

_IOClasses = (io.TextIOBase, io.BufferedIOBase, io.RawIOBase, io.IOBase)
"""The classes that should be treated as file-like classes"""

_STDIN_PATHS: List[str] = ["-", "stdin", "/dev/stdin"]
"""Paths that should be opened as standard input."""

_STDOUT_PATHS: List[str] = ["-", "stdout", "/dev/stdout"]
"""Paths that should be opened as standard output."""


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
        except StopIteration as ex:
            raise ValueError(f"Could not infer file type from {path}") from ex


def _pysam_open(
    path: SamPath,
    open_for_reading: bool,
    file_type: Optional[SamFileType] = None,
    unmapped: bool = False,
    **kwargs: Any,
) -> SamFile:
    """Opens a SAM/BAM/CRAM for reading or writing.

    This function permits reading from standard input and writing to standard output. The specified
    path may be the UNIX conventional `"-"`, the more explicit `"stdin"` or `"stdout"`, or an
    absolute path to either of the standard streams `"/dev/stdin"` or `"/dev/stdout"`.

    When writing to standard output, the file type must be specified.

    Args:
        path: a file handle or path to the SAM/BAM/CRAM to read or write.
        open_for_reading: True to open for reading, false otherwise.
        file_type: the file type to assume when opening the file.  If None, then the file type
            will be auto-detected for reading and must be a path-like object for writing.
        unmapped: True if the file is unmapped and has no sequence dictionary, False otherwise.
        kwargs: any keyword arguments to be passed to `pysam.AlignmentFile`; may not include "mode".
    """

    if isinstance(path, (str, Path)):
        if str(path) in _STDIN_PATHS and open_for_reading:
            path = sys.stdin
        elif str(path) in _STDOUT_PATHS and not open_for_reading:
            assert file_type is not None, "Must specify file_type when writing to standard output"
            path = sys.stdout
        else:
            if file_type is None:
                file_type = SamFileType.from_path(path)
            path = str(path)
    elif not isinstance(path, _IOClasses):
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

    if unmapped and open_for_reading:
        kwargs["check_sq"] = False

    # Open it alignment file, suppressing stderr in case index files are older than SAM file
    with fgpyo.io.suppress_stderr():
        alignment_file = pysam.AlignmentFile(path, **kwargs)
    # now restore stderr and return the alignment file
    return alignment_file


def reader(
    path: SamPath, file_type: Optional[SamFileType] = None, unmapped: bool = False
) -> SamFile:
    """Opens a SAM/BAM/CRAM for reading.

    To read from standard input, provide any of `"-"`, `"stdin"`, or `"/dev/stdin"` as the input
    `path`.

    Args:
        path: a file handle or path to the SAM/BAM/CRAM to read or write.
        file_type: the file type to assume when opening the file.  If None, then the file
            type will be auto-detected.
        unmapped: True if the file is unmapped and has no sequence dictionary, False otherwise.
    """
    return _pysam_open(path=path, open_for_reading=True, file_type=file_type, unmapped=unmapped)


def writer(
    path: SamPath,
    header: Union[str, Dict[str, Any], SamHeader],
    file_type: Optional[SamFileType] = None,
) -> SamFile:
    """Opens a SAM/BAM/CRAM for writing.

    To write to standard output, provide any of `"-"`, `"stdout"`, or `"/dev/stdout"` as the output
    `path`. **Note**: When writing to `stdout`, the `file_type` _must_ be given.

    Args:
        path: a file handle or path to the SAM/BAM/CRAM to read or write.
        header: Either a string to use for the header or a multi-level dictionary.  The
            multi-level dictionary should be given as follows.  The first level are the four
            types (‘HD’, ‘SQ’, ...). The second level are a list of lines, with each line being
            a list of tag-value pairs. The header is constructed first from all the defined
            fields, followed by user tags in alphabetical order.
        file_type: the file type to assume when opening the file.  If `None`, then the
            filetype will be auto-detected and must be a path-like object. This argument is required
            when writing to standard output.
    """
    # Set the header for pysam's AlignmentFile
    key = "text" if isinstance(header, str) else "header"
    kwargs = {key: header}

    return _pysam_open(
        path=path, open_for_reading=False, file_type=file_type, unmapped=False, **kwargs
    )


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
        code (int): The `~pysam` cigar operator code.
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

    @property
    def is_clipping(self) -> bool:
        """Returns true if the operator is a soft/hard clip, false otherwise."""
        return self == CigarOp.S or self == CigarOp.H


@attr.s(frozen=True, slots=True, auto_attribs=True)
class CigarElement:
    """Represents an element in a Cigar

    Attributes:
        - length (int): the length of the element
        - operator (CigarOp): the operator of the element
    """

    length: int
    operator: CigarOp

    def __attrs_post_init__(self) -> None:
        """Validates the length attribute is greater than zero."""
        if self.length <= 0:
            raise ValueError(f"Cigar element must have a length > 0, found {self.length}")

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


@attr.s(frozen=True, slots=True, auto_attribs=True)
class Cigar:
    """Class representing a cigar string.

    Attributes:
        - elements (Tuple[CigarElement, ...]): zero or more cigar elements
    """

    elements: Tuple[CigarElement, ...] = ()

    @classmethod
    def from_cigartuples(cls, cigartuples: Optional[List[Tuple[int, int]]]) -> "Cigar":
        """Returns a Cigar from a list of tuples returned by pysam.

        Each tuple denotes the operation and length.  See
        [`CigarOp()`][fgpyo.sam.CigarOp] for more information on the
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
                raise cls._pretty_cigarstring_exception(cigarstring, i)
            length = int(cigarstring[i])
            i += 1
            while i < cigarstring_length and cigarstring[i].isdigit():
                length = (length * 10) + int(cigarstring[i])
                i += 1
            if i == cigarstring_length:
                raise cls._pretty_cigarstring_exception(cigarstring, i)
            try:
                operator = CigarOp.from_character(cigarstring[i])
                elements.append(CigarElement(length, operator))
            except KeyError as ex:
                # cigar operator was not valid
                raise cls._pretty_cigarstring_exception(cigarstring, i) from ex
            except IndexError as ex:
                # missing cigar operator (i == len(cigarstring))
                raise cls._pretty_cigarstring_exception(cigarstring, i) from ex
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

    def query_alignment_offsets(self) -> Tuple[int, int]:
        """
        Gets the 0-based, end-exclusive positions of the first and last aligned base in the query.

        The resulting range will contain the range of positions in the SEQ string for
        the bases that are aligned.
        If counting from the end of the query is desired, use
        `cigar.reversed().query_alignment_offsets()`

        Returns:
            A tuple (start, stop) containing the start and stop positions
                of the aligned part of the query. These offsets are 0-based and open-ended, with
                respect to the beginning of the query.

        Raises:
            ValueError: If according to the cigar, there are no aligned query bases.
        """
        start_offset: int = 0
        end_offset: int = 0
        element: CigarElement
        alignment_began = False
        for element in self.elements:
            if element.operator.is_clipping and not alignment_began:
                # We are in the clipping operators preceding the alignment
                # Note: hardclips have length-on-query=0
                start_offset += element.length_on_query
                end_offset += element.length_on_query
            elif not element.operator.is_clipping:
                # We are within the alignment
                alignment_began = True
                end_offset += element.length_on_query
            else:
                # We have exited the alignment and are in the clipping operators after the alignment
                break

        if start_offset == end_offset:
            raise ValueError(f"Cigar {self} has no aligned bases")
        return start_offset, end_offset

    def __getitem__(
        self, index: Union[int, slice]
    ) -> Union[CigarElement, Tuple[CigarElement, ...]]:
        """Returns the cigar element indexed by index

        Arguments:
            index: int The index of the requested cigar element(s)

        Returns: CigarElement or Tuple[CigarElement,...]
            The element(s) selected by index

        Throws:
            TypeError if index isn't an integer or a slice
            IndexError: if there's no such element

        """
        return self.elements[index]


@enum.unique
class PairOrientation(enum.Enum):
    """Enumerations of read pair orientations."""

    FR = "FR"
    """A pair orientation for forward-reverse reads ("innie")."""

    RF = "RF"
    """A pair orientation for reverse-forward reads ("outie")."""

    TANDEM = "TANDEM"
    """A pair orientation for tandem (forward-forward or reverse-reverse) reads."""

    @classmethod
    def from_recs(  # noqa: C901  # `from_recs` is too complex (11 > 10)
        cls, rec1: AlignedSegment, rec2: Optional[AlignedSegment] = None
    ) -> Optional["PairOrientation"]:
        """Returns the pair orientation if both reads are mapped to the same reference sequence.

        Args:
            rec1: The first record in the pair.
            rec2: The second record in the pair. If None, then mate info on `rec1` will be used.

        See:
            [`htsjdk.samtools.SamPairUtil.getPairOrientation()`](https://github.com/samtools/htsjdk/blob/c31bc92c24bc4e9552b2a913e52286edf8f8ab96/src/main/java/htsjdk/samtools/SamPairUtil.java#L71-L102)
        """

        if rec2 is None:
            rec2_is_unmapped = rec1.mate_is_unmapped
            rec2_reference_id = rec1.next_reference_id
        else:
            rec2_is_unmapped = rec2.is_unmapped
            rec2_reference_id = rec2.reference_id

        if rec1.is_unmapped or rec2_is_unmapped or rec1.reference_id != rec2_reference_id:
            return None

        if rec2 is None:
            rec2_is_forward = rec1.mate_is_forward
            rec2_reference_start = rec1.next_reference_start
        else:
            rec2_is_forward = rec2.is_forward
            rec2_reference_start = rec2.reference_start

        if rec1.is_forward is rec2_is_forward:
            return PairOrientation.TANDEM
        if rec1.is_forward and rec1.reference_start <= rec2_reference_start:
            return PairOrientation.FR
        if rec1.is_reverse and rec2_reference_start < rec1.reference_end:
            return PairOrientation.FR
        if rec1.is_reverse and rec2_reference_start >= rec1.reference_end:
            return PairOrientation.RF

        if rec2 is None:
            if not rec1.has_tag("MC"):
                raise ValueError('Cannot determine pair orientation without a mate cigar ("MC")!')
            rec2_cigar = Cigar.from_cigarstring(str(rec1.get_tag("MC")))
            rec2_reference_end = rec1.next_reference_start + rec2_cigar.length_on_target()
        else:
            rec2_reference_end = rec2.reference_end

        if rec1.reference_start < rec2_reference_end:
            return PairOrientation.FR
        else:
            return PairOrientation.RF


def isize(rec1: AlignedSegment, rec2: Optional[AlignedSegment] = None) -> int:
    """Computes the insert size ("template length" or "TLEN") for a pair of records.

    Args:
        rec1: The first record in the pair.
        rec2: The second record in the pair. If None, then mate info on `rec1` will be used.
    """
    if rec2 is None:
        rec2_is_unmapped = rec1.mate_is_unmapped
        rec2_reference_id = rec1.next_reference_id
    else:
        rec2_is_unmapped = rec2.is_unmapped
        rec2_reference_id = rec2.reference_id

    if rec1.is_unmapped or rec2_is_unmapped or rec1.reference_id != rec2_reference_id:
        return 0

    if rec2 is None:
        rec2_is_forward = rec1.mate_is_forward
        rec2_reference_start = rec1.next_reference_start
    else:
        rec2_is_forward = rec2.is_forward
        rec2_reference_start = rec2.reference_start

    if rec1.is_forward and rec2_is_forward:
        return rec2_reference_start - rec1.reference_start
    if rec1.is_reverse and rec2_is_forward:
        return rec2_reference_start - rec1.reference_end

    if rec2 is None:
        if not rec1.has_tag("MC"):
            raise ValueError('Cannot determine proper pair status without a mate cigar ("MC")!')
        rec2_cigar = Cigar.from_cigarstring(str(rec1.get_tag("MC")))
        rec2_reference_end = rec1.next_reference_start + rec2_cigar.length_on_target()
    else:
        rec2_reference_end = rec2.reference_end

    if rec1.is_forward:
        return rec2_reference_end - rec1.reference_start
    else:
        return rec2_reference_end - rec1.reference_end


DefaultProperlyPairedOrientations: set[PairOrientation] = {PairOrientation.FR}
"""The default orientations for properly paired reads."""


def is_proper_pair(
    rec1: AlignedSegment,
    rec2: Optional[AlignedSegment] = None,
    max_insert_size: int = 1000,
    orientations: Collection[PairOrientation] = DefaultProperlyPairedOrientations,
    isize: Callable[[AlignedSegment, AlignedSegment], int] = isize,
) -> bool:
    """Determines if a pair of records are properly paired or not.

    Criteria for records in a proper pair are:
        - Both records are aligned
        - Both records are aligned to the same reference sequence
        - The pair orientation of the records is one of the valid pair orientations (default "FR")
        - The inferred insert size is not more than a maximum length (default 1000)

    Args:
        rec1: The first record in the pair.
        rec2: The second record in the pair. If None, then mate info on `rec1` will be used.
        max_insert_size: The maximum insert size to consider a pair "proper".
        orientations: The valid set of orientations to consider a pair "proper".
        isize: A function that takes the two alignments and calculates their isize.

    See:
        [`htsjdk.samtools.SamPairUtil.isProperPair()`](https://github.com/samtools/htsjdk/blob/c31bc92c24bc4e9552b2a913e52286edf8f8ab96/src/main/java/htsjdk/samtools/SamPairUtil.java#L106-L125)
    """
    if rec2 is None:
        rec2_is_mapped = rec1.mate_is_mapped
        rec2_reference_id = rec1.next_reference_id
    else:
        rec2_is_mapped = rec2.is_mapped
        rec2_reference_id = rec2.reference_id

    return (
        rec1.is_mapped
        and rec2_is_mapped
        and rec1.reference_id == rec2_reference_id
        and PairOrientation.from_recs(rec1=rec1, rec2=rec2) in orientations
        and 0 < abs(isize(rec1, rec2)) <= max_insert_size
    )


@attr.s(frozen=True, auto_attribs=True)
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

    reference_name: str
    start: int
    is_forward: bool
    cigar: Cigar
    mapq: int
    nm: int

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

    @property
    def end(self) -> int:
        """The 0-based exclusive end position of the alignment."""
        return self.start + self.cigar.length_on_target()

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

    @classmethod
    def from_read(cls, read: pysam.AlignedSegment) -> List["SupplementaryAlignment"]:
        """
        Construct a list of SupplementaryAlignments from the SA tag in a pysam.AlignedSegment.

        Args:
            read: An alignment. The presence of the "SA" tag is not required.

        Returns:
            A list of all SupplementaryAlignments present in the SA tag.
            If the SA tag is not present, or it is empty, an empty list will be returned.
        """
        if read.has_tag("SA"):
            sa_tag: str = cast(str, read.get_tag("SA"))
            return cls.parse_sa_tag(sa_tag)
        else:
            return []


def sum_of_base_qualities(rec: AlignedSegment, min_quality_score: int = 15) -> int:
    """Calculate the sum of base qualities score for an alignment record.

    This function is useful for calculating the "mate score" as implemented in `samtools fixmate`.
    Consistently with `samtools fixmate`, this function returns 0 if the record has no base
    qualities.

    Args:
        rec: The alignment record to calculate the sum of base qualities from.
        min_quality_score: The minimum base quality score to use for summation.

    Returns:
        The sum of base qualities on the input record. 0 if the record has no base qualities.

    See:
        [`calc_sum_of_base_qualities()`](https://github.com/samtools/samtools/blob/4f3a7397a1f841020074c0048c503a01a52d5fa2/bam_mate.c#L227-L238)
        [`MD_MIN_QUALITY`](https://github.com/samtools/samtools/blob/4f3a7397a1f841020074c0048c503a01a52d5fa2/bam_mate.c#L42)
    """
    if rec.query_qualities is None or rec.query_qualities == NO_QUERY_QUALITIES:
        return 0

    score: int = sum(qual for qual in rec.query_qualities if qual >= min_quality_score)
    return score


def _set_common_mate_fields(dest: AlignedSegment, mate_primary: AlignedSegment) -> None:
    """Set common mate info on a destination alignment from its mate's primary alignment.

    Args:
        dest: The alignment to set the mate info upon.
        mate_primary: The primary alignment to use as a mate reference.

    Raises:
        ValueError: If dest and mate_primary are of the same read ordinal.
        ValueError: If mate_primary is secondary or supplementary.
        ValueError: If dest and mate_primary do not share the same query name.
    """
    if mate_primary.is_read1 is dest.is_read1:
        raise ValueError("mate_primary and dest records must be of different read ordinals!")
    if mate_primary.is_supplementary or mate_primary.is_secondary:
        raise ValueError("Mate info must be set from a non-supplementary non-secondary record!")
    if mate_primary.query_name != dest.query_name:
        raise ValueError("Cannot set mate info on alignments with different query names!")

    dest.next_reference_id = mate_primary.reference_id
    dest.next_reference_name = mate_primary.reference_name
    dest.next_reference_start = mate_primary.reference_start
    dest.mate_is_forward = mate_primary.is_forward
    dest.mate_is_mapped = mate_primary.is_mapped
    dest.set_tag("MC", mate_primary.cigarstring)
    dest.set_tag("MQ", mate_primary.mapping_quality)
    dest.set_tag("ms", sum_of_base_qualities(mate_primary))


def set_mate_info(
    rec1: AlignedSegment,
    rec2: AlignedSegment,
    is_proper_pair: Callable[[AlignedSegment, AlignedSegment], bool] = is_proper_pair,
    isize: Callable[[AlignedSegment, AlignedSegment], int] = isize,
) -> None:
    """Resets mate pair information between two primary alignments that share a query name.

    Args:
        rec1: The first record in the pair.
        rec2: The second record in the pair.
        is_proper_pair: A function that takes the two alignments and determines proper pair status.
        isize: A function that takes the two alignments and calculates their isize.

    Raises:
        ValueError: If rec1 and rec2 are of the same read ordinal.
        ValueError: If either rec1 or rec2 is secondary or supplementary.
        ValueError: If rec1 and rec2 do not share the same query name.
    """
    for dest, source in [(rec1, rec2), (rec2, rec1)]:
        _set_common_mate_fields(dest=dest, mate_primary=source)

    template_length = isize(rec1, rec2)
    rec1.template_length = template_length
    rec2.template_length = -template_length

    proper_pair = is_proper_pair(rec1, rec2)
    rec1.is_proper_pair = proper_pair
    rec2.is_proper_pair = proper_pair


def set_mate_info_on_secondary(secondary: AlignedSegment, mate_primary: AlignedSegment) -> None:
    """Set mate info on a secondary alignment from its mate's primary alignment.

    Args:
        secondary: The secondary alignment to set mate information upon.
        mate_primary: The primary alignment of the secondary's mate.

    Raises:
        ValueError: If secondary and mate_primary are of the same read ordinal.
        ValueError: If secondary and mate_primary do not share the same query name.
        ValueError: If mate_primary is secondary or supplementary.
        ValueError: If secondary is not marked as a secondary alignment.
    """
    if not secondary.is_secondary:
        raise ValueError("Cannot set mate info on an alignment not marked as secondary!")

    _set_common_mate_fields(dest=secondary, mate_primary=mate_primary)


def set_mate_info_on_supplementary(supp: AlignedSegment, mate_primary: AlignedSegment) -> None:
    """Set mate info on a supplementary alignment from its mate's primary alignment.

    Args:
        supp: The supplementary alignment to set mate information upon.
        mate_primary: The primary alignment of the supplementary's mate.

    Raises:
        ValueError: If supp and mate_primary are of the same read ordinal.
        ValueError: If supp and mate_primary do not share the same query name.
        ValueError: If mate_primary is secondary or supplementary.
        ValueError: If supp is not marked as a supplementary alignment.
    """
    if not supp.is_supplementary:
        raise ValueError("Cannot set mate info on an alignment not marked as supplementary!")

    _set_common_mate_fields(dest=supp, mate_primary=mate_primary)

    # NB: for a non-secondary supplemental alignment, set the following to the same as the primary.
    if not supp.is_secondary:
        supp.is_proper_pair = mate_primary.is_proper_pair
        supp.template_length = -mate_primary.template_length


@deprecated("Use `set_mate_info()` instead. Deprecated after fgpyo 0.8.0.")
def set_pair_info(r1: AlignedSegment, r2: AlignedSegment, proper_pair: bool = True) -> None:
    """Resets mate pair information between reads in a pair.

    Can be handed reads that already have pairing flags setup or independent R1 and R2 records that
    are currently flagged as SE reads.

    Args:
        r1: Read 1 (first read in the template).
        r2: Read 2 with the same query name as r1 (second read in the template).
        proper_pair: whether the pair is proper or not.
    """
    if r1.query_name != r2.query_name:
        raise ValueError("Cannot set pair info on reads with different query names!")

    for r in [r1, r2]:
        r.is_paired = True

    r1.is_read1 = True
    r1.is_read2 = False
    r2.is_read2 = True
    r2.is_read1 = False

    set_mate_info(rec1=r1, rec2=r2, is_proper_pair=lambda a, b: proper_pair)


@attr.s(frozen=True, auto_attribs=True)
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


@attr.s(frozen=True, auto_attribs=True)
class Template:
    """A container for alignment records corresponding to a single sequenced template
    or insert.

    It is strongly preferred that new Template instances be created with `Template.build()`
    which will ensure that reads are stored in the correct Template property, and run basic
    validations of the Template by default.  If constructing Template instances by construction
    users are encouraged to use the validate method post-construction.

    In the special cases there are alignments records that are _*both secondary and supplementary*_
    then they will be stored upon the `r1_supplementals` and `r2_supplementals` fields only.

    Attributes:
        name: the name of the template/query
        r1: Primary non-supplementary alignment for read 1, or None if there is none
        r2: Primary non-supplementary alignment for read 2, or None if there is none
        r1_supplementals: Supplementary alignments for read 1
        r2_supplementals: Supplementary alignments for read 2
        r1_secondaries: Secondary (non-primary, non-supplementary) alignments for read 1
        r2_secondaries: Secondary (non-primary, non-supplementary) alignments for read 2
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
            elif rec.is_secondary:
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
            assert not rec.is_supplementary, "R1 secondary supplementals belong with supplementals"

        for rec in self.r1_supplementals:
            assert rec.is_read1 or not rec.is_paired, "R1 supp. not flagged as R1 or unpaired"
            assert rec.is_supplementary, "R1 supp. not flagged as supplementary"

        for rec in self.r2_secondaries:
            assert rec.is_read2, "R2 secondary not flagged as R2"
            assert rec.is_secondary, "R2 secondary not flagged as secondary"
            assert not rec.is_supplementary, "R2 secondary supplementals belong with supplementals"

        for rec in self.r2_supplementals:
            assert rec.is_read2, "R2 supp. not flagged as R2"
            assert rec.is_supplementary, "R2 supp. not flagged as supplementary"

    def primary_recs(self) -> Iterator[AlignedSegment]:
        """Returns a list with all the primary records for the template."""
        return (r for r in (self.r1, self.r2) if r is not None)

    def all_r1s(self) -> Iterator[AlignedSegment]:
        """Yields all R1 alignments of this template including secondary and supplementary."""
        r1_primary = [] if self.r1 is None else [self.r1]
        return chain(r1_primary, self.r1_secondaries, self.r1_supplementals)

    def all_r2s(self) -> Iterator[AlignedSegment]:
        """Yields all R2 alignments of this template including secondary and supplementary."""
        r2_primary = [] if self.r2 is None else [self.r2]
        return chain(r2_primary, self.r2_secondaries, self.r2_supplementals)

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

    def set_mate_info(
        self,
        is_proper_pair: Callable[[AlignedSegment, AlignedSegment], bool] = is_proper_pair,
        isize: Callable[[AlignedSegment, AlignedSegment], int] = isize,
    ) -> Self:
        """Reset all mate information on every alignment in the template.

        Args:
            is_proper_pair: A function that takes two alignments and determines proper pair status.
            isize: A function that takes the two alignments and calculates their isize.
        """
        if self.r1 is not None and self.r2 is not None:
            set_mate_info(self.r1, self.r2, is_proper_pair=is_proper_pair, isize=isize)
        if self.r1 is not None:
            for rec in self.r2_secondaries:
                set_mate_info_on_secondary(secondary=rec, mate_primary=self.r1)
            for rec in self.r2_supplementals:
                set_mate_info_on_supplementary(supp=rec, mate_primary=self.r1)
        if self.r2 is not None:
            for rec in self.r1_secondaries:
                set_mate_info_on_secondary(secondary=rec, mate_primary=self.r2)
            for rec in self.r1_supplementals:
                set_mate_info_on_supplementary(supp=rec, mate_primary=self.r2)
        return self

    def write_to(
        self,
        writer: SamFile,
        primary_only: bool = False,
    ) -> None:
        """Write the records associated with the template to file.

        Args:
            writer: An open, writable AlignmentFile.
            primary_only: If True, only write primary alignments.
        """

        if primary_only:
            rec_iter = self.primary_recs()
        else:
            rec_iter = self.all_recs()

        for rec in rec_iter:
            writer.write(rec)

    def set_tag(
        self,
        tag: str,
        value: Union[str, int, float, None],
    ) -> None:
        """Add a tag to all records associated with the template.

        Setting a tag to `None` will remove the tag.

        Args:
            tag: The name of the tag.
            value: The value of the tag.
        """

        assert len(tag) == 2, f"Tags must be 2 characters: {tag}."

        for rec in self.all_recs():
            rec.set_tag(tag, value)


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


class SamOrder(enum.Enum):
    """
    Enumerations of possible sort orders for a SAM file.
    """

    Unsorted = "unsorted"  #: the SAM / BAM / CRAM is unsorted
    Coordinate = "coordinate"  #: coordinate sorted
    QueryName = "queryname"  #: queryname sorted
    Unknown = "unknown"  # Unknown SAM / BAM / CRAM sort order
