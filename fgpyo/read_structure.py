"""
Classes for representing Read Structures
----------------------------------------

A Read Structure refers to a String that describes how the bases in a sequencing run should be
allocated into logical reads.  It serves a similar purpose to the --use-bases-mask in Illumina's
`bcltofastq` software, but provides some additional capabilities.

A Read Structure is a sequence of `<number><operator>` pairs or segments where, optionally, the last
segment in the string is allowed to use `+` instead of a number for its length. The `+` translates
to whatever bases are left after the other segments are processed and can be thought of as meaning
`[0..infinity]`.

See more at: https://github.com/fulcrumgenomics/fgbio/wiki/Read-Structures

Examples
~~~~~~~~
.. code-block:: python

   >>> from fgpyo.read_structure import ReadStructure
   >>> rs = ReadStructure.from_string("75T8B75T")
   >>> [str(segment) for segment in rs]
   '75T', '8B', '75T'
   >>> rs[0]
   ReadSegment(offset=0, length=75, kind=<SegmentType.Template: 'T'>)
   >>> rs = rs.with_variable_last_segment()
   >>> [str(segment) for segment in rs]
   ['75T', '8B', '+T']
   >>> rs[-1]
   ReadSegment(offset=83, length=None, kind=<SegmentType.Template: 'T'>)
   >>> rs = ReadStructure.from_string("1B2M+T")
   >>> [s.bases for s in rs.extract("A"*6)]
   ['A', 'AA', 'AAA']
   >>> [s.bases for s in rs.extract("A"*5)]
   ['A', 'AA', 'AA']
   >>> [s.bases for s in rs.extract("A"*4)]
   ['A', 'AA', 'A']
   >>> [s.bases for s in rs.extract("A"*3)]
   ['A', 'AA', '']
   >>> rs.template_segments()
   (ReadSegment(offset=3, length=None, kind=<SegmentType.Template: 'T'>),)
   >>> [str(segment) for segment in rs.template_segments()]
   ['+T']
   >>> try:
   ...   ReadStructure.from_string("23T2TT23T")
   ... except ValueError as ex:
   ...   print(str(ex))
   ...
   Read structure missing length information: 23T2T[T]23T

Module Contents
~~~~~~~~~~~~~~~
The module contains the following public classes:
    - :class:`~fgpyo.read_structure.ReadStructure` -- Describes the structure of a give read
    - :class:`~fgpyo.read_structure.ReadSegment` -- Describes all the information about a segment
        within a read structure
    - :class:`~fgpyo.read_structure.SegmentType` -- The type of segments that can show up in a read
        structure
    - :class:`~fgpyo.read_structure.SubReadWithoutQuals` -- Contains the bases that correspond to
        the given read segment
    - :class:`~fgpyo.read_structure.SubReadWithQuals` -- Contains the bases and qualities that
        correspond to the given read segment
"""
import enum
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple

import attr

# A character that can be put in place of a number in a read structure to mean "0 or more bases".
ANY_LENGTH_CHAR: str = "+"


@enum.unique
class SegmentType(enum.Enum):
    """The type of segments that can show up in a read structure"""

    Template = "T"
    SampleBarcode = "B"
    MolecularBarcode = "M"
    Skip = "S"

    def __str__(self) -> str:
        return self.value


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class SubReadWithoutQuals:
    """Contains the bases that correspond to the given read segment"""

    bases: str
    segment: "ReadSegment"

    @property
    def kind(self) -> SegmentType:
        return self.segment.kind


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class SubReadWithQuals:
    """Contains the bases and qualities that correspond to the given read segment"""

    bases: str
    quals: str
    segment: "ReadSegment"

    @property
    def kind(self) -> SegmentType:
        return self.segment.kind


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class ReadSegment:
    """Encapsulates all the information about a segment within a read structure. A segment can
    either have a definite length, in which case length must be Some(Int), or an indefinite length
    (can be any length, 0 or more) in which case length must be None.

    Attributes:
        offset: the offset of the read segment in the read
        length: the length of the segment, or None if it is variable length
        kind: the kind of read segment
    """

    offset: int
    length: Optional[int]
    kind: SegmentType

    @property
    def has_fixed_length(self) -> bool:
        """True if the read segment has a defined length."""
        return self.length is not None

    @property
    def fixed_length(self) -> int:
        """The fixed length if there is one. Throws an exception on segments without fixed
        lengths!"""
        if not self.has_fixed_length:
            raise AttributeError(f"fixed_length called on a variable length segment: {self}")
        return self.length

    def extract(self, bases: str) -> SubReadWithoutQuals:
        """Gets the bases associated with this read segment.  If strict is false then only return
        the sub-sequence for which we have bases in `bases`, otherwise throw an exception.
        """
        end = self._calculate_end(bases)
        return SubReadWithoutQuals(bases=bases[self.offset : end], segment=self._resized(end))

    def extract_with_quals(self, bases: str, quals: str) -> SubReadWithQuals:
        """Gets the bases and qualities associated with this read segment.  If strict is false then
        only return the sub-sequence for which we have bases in `bases`, otherwise throw an
        exception."""
        assert len(bases) == len(quals), f"Bases and quals differ in length: {bases} {quals}"
        end = self._calculate_end(bases)
        return SubReadWithQuals(
            bases=bases[self.offset : end],
            quals=quals[self.offset : end],
            segment=self._resized(end),
        )

    def _calculate_end(self, bases: str) -> int:
        """Checks some requirements and then calculates the end position for the segment for the
        given read"""
        bases_len = len(bases)
        assert bases_len >= self.offset, f"Read ends before the segment starts: {self}"
        assert (
            self.length is None or bases_len >= self.offset + self.length
        ), f"Read ends before end of segment: {self}"
        if self.has_fixed_length:
            return min(self.offset + self.fixed_length, bases_len)
        else:
            return bases_len

    def _resized(self, end: int) -> "ReadSegment":
        new_length = end - self.offset
        if self.has_fixed_length and self.fixed_length == new_length:
            return self
        else:
            return attr.evolve(self, length=new_length)

    def __str__(self) -> str:
        if self.has_fixed_length:
            return f"{self.length}{self.kind.value}"
        else:
            return f"{ANY_LENGTH_CHAR}{self.kind.value}"


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class ReadStructure(Iterable[ReadSegment]):
    """Describes the structure of a give read.  A read contains one or more read segments. A read
    segment describes a contiguous stretch of bases of the same type (ex. template bases) of some
    length and some offset from the start of the read.

    Attributes:
         segments: the segments composing the read structure
    """

    segments: Tuple[ReadSegment, ...]

    @property
    def _min_length(self) -> int:
        """The minimum length read that this read structure can process"""
        return sum(segment.length for segment in self.segments if segment.has_fixed_length)

    @property
    def has_fixed_length(self) -> bool:
        """True if the ReadStructure has a fixed (i.e. non-variable) length"""
        return self.segments[-1].has_fixed_length

    @property
    def fixed_length(self) -> int:
        """The fixed length if there is one. Throws an exception on segments without fixed
        lengths!"""
        if not self.has_fixed_length:
            raise AttributeError(
                f"fixed_length called on a variable length read structure: {self}"
            )
        return self._min_length

    @property
    def length(self) -> int:
        """Length is defined as the number of segments (not bases!) in the read structure"""
        return len(self.segments)

    def with_variable_last_segment(self) -> "ReadStructure":
        """Generates a new ReadStructure that is the same as this one except that the last segment
        has undefined length"""
        last_segment = self.segments[-1]
        if not last_segment.has_fixed_length:
            return self
        else:
            last_segment = attr.evolve(last_segment, length=None)
            return ReadStructure(segments=self.segments[:-1] + (last_segment,))

    def extract(self, bases: str) -> Tuple[SubReadWithoutQuals, ...]:
        """Splits the given bases into tuples with its associated read segment."""
        return tuple([segment.extract(bases=bases) for segment in self])

    def extract_with_quals(self, bases: str, quals: str) -> Tuple[SubReadWithQuals, ...]:
        """Splits the given bases and qualities into triples with its associated read segment."""
        return tuple([segment.extract_with_quals(bases=bases, quals=quals) for segment in self])

    def segments_by_kind(self, kind: SegmentType) -> Tuple[ReadSegment, ...]:
        """Returns just the segments of a given kind."""
        return tuple([segment for segment in self if segment.kind == kind])

    def template_segments(self) -> Tuple[ReadSegment, ...]:
        return self.segments_by_kind(kind=SegmentType.Template)

    def sample_barcode_segments(self) -> Tuple[ReadSegment, ...]:
        return self.segments_by_kind(kind=SegmentType.SampleBarcode)

    def molecular_barcode_segments(self) -> Tuple[ReadSegment, ...]:
        return self.segments_by_kind(kind=SegmentType.MolecularBarcode)

    def skip_segments(self) -> Tuple[ReadSegment, ...]:
        return self.segments_by_kind(kind=SegmentType.Skip)

    def __iter__(self) -> Iterator[ReadSegment]:
        return iter(self.segments)

    def __str__(self) -> str:
        return "".join(str(s) for s in self.segments)

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, index: int) -> ReadSegment:
        return self.segments[index]

    @classmethod
    def from_segments(
        cls, segments: Tuple[ReadSegment, ...], reset_offsets: bool = False
    ) -> "ReadStructure":
        """Creates a new ReadStructure, optionally resetting the offsets on each of the segments"""
        # Check that none but the last segment has an indefinite length
        assert all(s.has_fixed_length for s in segments[:-1]), (
            f"Variable length ({ANY_LENGTH_CHAR}) can only be used in the last segment: "
            + "".join(str(s) for s in segments)
        )

        if reset_offsets:
            off = 0
            segs = []
            for seg in segments:
                seg = attr.evolve(seg, offset=off)
                off += seg.length if seg.has_fixed_length else 0
                segs.append(seg)
            segments = tuple(segs)

        assert all(
            s.length is None or s.length > 0 for s in segments
        ), "Read structure contained zero length segments" + "".join(str(s) for s in segments)

        return ReadStructure(segments=segments)

    @classmethod
    def from_string(cls, segments: str) -> "ReadStructure":
        # Check that none but the last segment has an indefinite length
        tidied = "".join(ch for ch in segments.upper() if not ch.isspace())
        return cls.from_segments(segments=cls._from_string(string=tidied), reset_offsets=True)

    @classmethod
    def _from_string(cls, string: str) -> Tuple[ReadSegment, ...]:
        index = 0
        segments: List[ReadSegment] = []
        while index < len(string):
            # tash the beginning position of our parsing so we can highlight what we're having
            # trouble with
            parse_index = index

            seg_length: Optional[int] = None
            # Parse out the length segment which many be 1 or more digits or the AnyLengthChar
            if string[index] == ANY_LENGTH_CHAR:
                index += 1
                seg_length = None
            elif string[index].isdigit():
                seg_length = 0
                while index < len(string) and string[index].isdigit():
                    seg_length = (seg_length * 10) + int(string[index])
                    index += 1
            else:
                cls._invalid(
                    msg="Read structure missing length information",
                    rs=string,
                    start=parse_index,
                    end=parse_index + 1,
                )

            # Parse out the operator and make a segment
            if index == len(string):
                cls._invalid(
                    msg="Read structure with invalid segment",
                    rs=string,
                    start=parse_index,
                    end=index,
                )
            code = string[index]
            index += 1
            kind: SegmentType
            try:
                kind = SegmentType(code)
            except ValueError:
                cls._invalid(
                    msg="Read structure segment had unknown type",
                    rs=string,
                    start=parse_index,
                    end=parse_index + 1,
                )
            segments.append(ReadSegment(offset=0, length=seg_length, kind=kind))

        return tuple(segments)

    @classmethod
    def _invalid(cls, msg: str, rs: str, start: int, end: int) -> None:
        """Inserts square brackets around the characters in the read structure that are causing the
        error."""
        prefix = rs[:start]
        error = rs[start:end]
        suffix = "" if end == len(rs) else rs[end:]
        raise ValueError(f"{msg}: {prefix}[{error}]{suffix}")
