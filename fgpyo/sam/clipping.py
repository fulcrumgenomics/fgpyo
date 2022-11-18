"""
Utility Functions for Soft-Clipping records in SAM/BAM Files
------------------------------------------------------------

This module contains utility functions for soft-clipping reads.  There are four variants
that support clipping the beginnings and ends of reads, and specifying the amount to be
clipped in terms of query bases or reference bases:

    - :func:`~fgpyo.clipping.softclip_start_of_alignment_by_query` clips the start
      of the alignment in terms of query bases
    - :func:`~fgpyo.clipping.softclip_end_of_alignment_by_query` clips the end
      of the alignment in terms of query bases
    - :func:`~fgpyo.clipping.softclip_start_of_alignment_by_ref` clips the start
      of the alignment in terms of reference bases
    - :func:`~fgpyo.clipping.softclip_end_of_alignment_by_ref` clips the end
      of the alignment in terms of reference bases

The difference between query and reference based versions is apparent only when there are
insertions or deletions in the read as indels have lengths on either the query (insertions) or
reference (deletions) but not both.

Upon clipping a set of additional SAM tags are removed from reads as they are likely invalid.

For example, to clip the last 10 query bases of all records and reduce the qualities to Q2:

.. code-block:: python


    >>> from fgpyo.sam import reader, clipping
    >>> with reader("/path/to/sample.sam") as fh:
    ...     for rec in fh:
    ...         clipping.softclip_end_of_alignment_by_query(rec, 10, 2)
    ...         print(rec.cigarstring)

It should be noted that any clipping potentially makes the common SAM tags NM, MD and UQ
invalid, as well as potentially other alignment based SAM tags.  Any clipping added to the start
of an alignment changes the position (reference_start) of the record. Any reads that have no
aligned bases after clipping are set to be unmapped.  If writing the clipped reads back to a BAM
it should be noted that:

    - Mate pairs may have incorrect information about their mate's positions
    - Even if the input was coordinate sorted, the output may be out of order

To rectify these problems it is necessary to do the equivalent of:

.. code-block:: bash

    cat clipped.bam | samtools sort -n | samtools fixmate | samtools sort | samtools calmd
"""

from array import array
from typing import Iterable
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Tuple

from pysam import AlignedSegment

from fgpyo import sam
from fgpyo.collections import PeekableIterator
from fgpyo.sam import Cigar
from fgpyo.sam import CigarElement
from fgpyo.sam import CigarOp
from fgpyo.sequence import reverse_complement

"""The default set of SAM tags which become invalid when clipping is applied."""
TAGS_TO_INVALIDATE: Iterable[str] = ("MD", "NM", "UQ")


class ClippingInfo(NamedTuple):
    """Named tuple holding the number of bases clipped on the query and reference respectively.

    Attributes:
        query_bases_clipped (int): the number of query bases in the alignment that were clipped.
        ref_bases_clipped (int): the number of reference bases in the alignment that were clipped.
    """

    query_bases_clipped: int
    ref_bases_clipped: int


def softclip_start_of_alignment_by_query(
    rec: AlignedSegment,
    bases_to_clip: int,
    clipped_base_quality: Optional[int] = None,
    tags_to_invalidate: Iterable[str] = TAGS_TO_INVALIDATE,
) -> ClippingInfo:
    """
    Adds soft-clipping to the start of a read's alignment.

    Clipping is applied after any existing hard or soft clipping.  E.g. a read with cigar 5S100M
    that is clipped with bases_to_clip=10 will yield a cigar of 15S90M.

    If the read is unmapped or bases_to_clip < 1 then nothing is done.

    If the read has fewer clippable bases than requested the read will be unmapped.

    Args:
        rec: the BAM record to clip
        bases_to_clip: the number of additional bases of clipping desired in the read/query
        clipped_base_quality: if not None, set bases in the clipped region to this quality
        tags_to_invalidate: the set of extended attributes to remove upon clipping

    Returns:
        ClippingInfo: a named tuple containing the number of query/read bases and the number
            of target/reference bases clipped.
    """
    if rec.is_unmapped or bases_to_clip < 1:
        return ClippingInfo(0, 0)

    num_clippable_bases = rec.query_alignment_length

    if bases_to_clip >= num_clippable_bases:
        return _clip_whole_read(rec, tags_to_invalidate)

    cigar = Cigar.from_cigartuples(rec.cigartuples)
    quals = rec.query_qualities
    new_cigar, clipping_info = _clip(cigar, quals, bases_to_clip, clipped_base_quality)
    rec.query_qualities = quals

    rec.reference_start += clipping_info.ref_bases_clipped
    rec.cigarstring = str(new_cigar)
    _cleanup(rec, tags_to_invalidate)
    return clipping_info


def softclip_end_of_alignment_by_query(
    rec: AlignedSegment,
    bases_to_clip: int,
    clipped_base_quality: Optional[int] = None,
    tags_to_invalidate: Iterable[str] = TAGS_TO_INVALIDATE,
) -> ClippingInfo:
    """
    Adds soft-clipping to the end of a read's alignment.

    Clipping is applied before any existing hard or soft clipping.  E.g. a read with cigar 100M5S
    that is clipped with bases_to_clip=10 will yield a cigar of 90M15S.

    If the read is unmapped or bases_to_clip < 1 then nothing is done.

    If the read has fewer clippable bases than requested the read will be unmapped.

    Args:
        rec: the BAM record to clip
        bases_to_clip: the number of additional bases of clipping desired in the read/query
        clipped_base_quality: if not None, set bases in the clipped region to this quality
        tags_to_invalidate: the set of extended attributes to remove upon clipping

    Returns:
        ClippingInfo: a named tuple containing the number of query/read bases and the number
            of target/reference bases clipped.
    """
    if rec.is_unmapped or bases_to_clip < 1:
        return ClippingInfo(0, 0)

    num_clippable_bases = rec.query_alignment_length

    if bases_to_clip >= num_clippable_bases:
        return _clip_whole_read(rec, tags_to_invalidate)

    # Reverse the cigar and qualities so we can clip from the start
    cigar = Cigar.from_cigartuples(rec.cigartuples).reversed()
    quals = rec.query_qualities
    quals.reverse()
    new_cigar, clipping_info = _clip(cigar, quals, bases_to_clip, clipped_base_quality)

    # Then reverse everything back again
    quals.reverse()
    rec.query_qualities = quals
    rec.cigarstring = str(new_cigar.reversed())

    _cleanup(rec, tags_to_invalidate)
    return clipping_info


def softclip_start_of_alignment_by_ref(
    rec: AlignedSegment,
    bases_to_clip: int,
    clipped_base_quality: Optional[int] = None,
    tags_to_invalidate: Iterable[str] = TAGS_TO_INVALIDATE,
) -> ClippingInfo:
    """Soft-clips the start of an alignment by bases_to_clip bases on the reference.

    Clipping is applied after any existing hard or soft clipping.  E.g. a read with cigar 5S100M
    that is clipped with bases_to_clip=10 will yield a cigar of 15S90M.

    If the read is unmapped or bases_to_clip < 1 then nothing is done.

    If the read has fewer clippable bases than requested the read will be unmapped.

    Args:
        rec: the BAM record to clip
        bases_to_clip: the number of additional bases of clipping desired on the reference
        clipped_base_quality: if not None, set bases in the clipped region to this quality
        tags_to_invalidate: the set of extended attributes to remove upon clipping

    Returns:
        ClippingInfo: a named tuple containing the number of query/read bases and the number
            of target/reference bases clipped.
    """
    if rec.reference_length <= bases_to_clip:
        return _clip_whole_read(rec, tags_to_invalidate)

    new_start = rec.reference_start + bases_to_clip
    new_query_start = _read_pos_at_ref_pos(rec, new_start, previous=False)
    query_bases_to_clip = new_query_start - rec.query_alignment_start
    return softclip_start_of_alignment_by_query(
        rec, query_bases_to_clip, clipped_base_quality, tags_to_invalidate
    )


def softclip_end_of_alignment_by_ref(
    rec: AlignedSegment,
    bases_to_clip: int,
    clipped_base_quality: Optional[int] = None,
    tags_to_invalidate: Iterable[str] = TAGS_TO_INVALIDATE,
) -> ClippingInfo:
    """Soft-clips the end of an alignment by bases_to_clip bases on the reference.

    Clipping is applied beforeany existing hard or soft clipping.  E.g. a read with cigar 100M5S
    that is clipped with bases_to_clip=10 will yield a cigar of 90M15S.

    If the read is unmapped or bases_to_clip < 1 then nothing is done.

    If the read has fewer clippable bases than requested the read will be unmapped.

    Args:
        rec: the BAM record to clip
        bases_to_clip: the number of additional bases of clipping desired on the reference
        clipped_base_quality: if not None, set bases in the clipped region to this quality
        tags_to_invalidate: the set of extended attributes to remove upon clipping

    Returns:
        ClippingInfo: a named tuple containing the number of query/read bases and the number
            of target/reference bases clipped.
    """
    if rec.reference_length <= bases_to_clip:
        return _clip_whole_read(rec, tags_to_invalidate)

    new_end = rec.reference_end - bases_to_clip
    new_query_end = _read_pos_at_ref_pos(rec, new_end, previous=False)
    query_bases_to_clip = rec.query_alignment_end - new_query_end
    return softclip_end_of_alignment_by_query(
        rec, query_bases_to_clip, clipped_base_quality, tags_to_invalidate
    )


def _clip_whole_read(rec: AlignedSegment, tags_to_invalidate: Iterable[str]) -> ClippingInfo:
    """Private method that unmaps a read and returns an appropriate ClippingInfo."""
    retval = ClippingInfo(rec.query_alignment_length, rec.reference_length)
    _cleanup(rec, tags_to_invalidate)
    _make_read_unmapped(rec)
    return retval


def _make_read_unmapped(rec: AlignedSegment) -> None:
    """Removes mapping information from a read."""
    if rec.is_reverse:
        quals = rec.query_qualities
        quals.reverse()
        rec.query_sequence = reverse_complement(rec.query_sequence)
        rec.query_qualities = quals
        rec.is_reverse = False

    rec.reference_id = sam.NO_REF_INDEX
    rec.reference_start = sam.NO_REF_POS
    rec.cigarstring = None
    rec.mapping_quality = 0
    rec.template_length = 0
    rec.is_duplicate = False
    rec.is_secondary = False
    rec.is_supplementary = False
    rec.is_proper_pair = False
    rec.is_unmapped = True


def _cleanup(rec: AlignedSegment, tags_to_invalidate: Iterable[str]) -> None:
    """Removes extended tags from a record that may have become invalid after clipping."""
    for tag in tags_to_invalidate:
        rec.set_tag(tag, None)


def _read_pos_at_ref_pos(
    rec: AlignedSegment, ref_pos: int, previous: Optional[bool] = None
) -> Optional[int]:
    """
    Returns the read or query position at the reference position.

    If the reference position is not within the span of reference positions to which the
    read is aligned an exception will be raised.  If the reference position is within the span
    but is not aligned (i.e. it is deleted in the read) behavior is controlled by the
    "previous" argument.

    Args:
        rec: the AlignedSegment within which to find the read position
        ref_pos: the reference position to be found
        previous: Controls behavior when the reference position is not aligned to any
            read position.  True indicates to return the previous read position, False
            indicates to return the next read position and None indicates to return None.

    Returns:
        The read position at the reference position, or None.
    """
    if ref_pos < rec.reference_start or ref_pos >= rec.reference_end:
        raise ValueError(f"{ref_pos} is not within the reference span for read {rec.query_name}")

    pairs = rec.get_aligned_pairs()
    index = 0
    read_pos = None
    for read, ref in pairs:
        if ref == ref_pos:
            read_pos = read
            break
        else:
            index += 1

    if not read_pos and previous is not None:
        if previous:
            while read_pos is None and index > 0:
                index -= 1
                read_pos = pairs[index][0]
        else:
            while read_pos is None and index < len(pairs):
                read_pos = pairs[index][0]
                index += 1

    return read_pos


def _clip(
    cigar: Cigar, quals: array, bases_to_clip: int, clipped_base_quality: Optional[int]
) -> Tuple[Cigar, ClippingInfo]:
    """Workhorse private clipping method that clips the start of cigars.

    Always works on the start of the cigars/quals; end-clipping is accomplished by
    reversing value before calling this function.  Since the function is private it
    makes the following assumptions:

    1. There are at least bases_to_clip bases available for clipping in the read
    2. The cigar and quals agree on the query length
    2. clipped_base_quality is either None or a valid integer base quality
    """

    if any(cig.operator == CigarOp.P for cig in cigar.elements):
        raise ValueError(f"Cannot handle cigars that contain padding: {cigar}")

    elems = PeekableIterator(cigar.elements)
    existing_hard_clips = elems.takewhile(lambda c: c.operator == CigarOp.H)
    existing_soft_clips = elems.takewhile(lambda c: c.operator == CigarOp.S)
    read_bases_clipped = 0
    ref_bases_clipped = 0
    new_elems: List[CigarElement] = []  # buffer of cigar elements used to make the returned cigar

    # Returns true if the operator immediately after the clipping point is a deletion
    def is_trailing_deletion() -> bool:
        # Four conditions must be met:
        # 1. The number of bases _to_ clip equals the number of bases _already_ clipped
        # 2. The clipping point falls between operators (i.e. new_elems is empty)
        # 3. There is at least one more element to consider.
        # 4. The next element is a deletion.
        return (
            read_bases_clipped == bases_to_clip
            and not new_elems
            and elems.peek() is not None
            and elems.peek().operator == CigarOp.D
        )

    # The loop skips over all operators that are getting turned into clipping, while keeping track
    # of how many reference bases and how many read bases are skipped over.  If the clipping point
    # falls between existing operators then the new_elems buffer is empty at the end of the while
    # loop. If the clip point falls within:
    #    a) an alignment operator then the operator is split and the remainder added to the buffer
    #    b) an insertion: the remainder of the insertion is also clipped
    # If the operator immediately after the clip is a deletion, it is also discarded.
    #
    # At the end of the while loop new_elems is either:
    #   a) Empty
    #   b) Contains a single element which is the remainder of an element that had to be split
    while read_bases_clipped < bases_to_clip or is_trailing_deletion():
        elem = next(elems)
        op: CigarOp = elem.operator
        length: int = elem.length
        remaining_to_clip = bases_to_clip - read_bases_clipped

        if op.consumes_query and length > remaining_to_clip:
            if op == CigarOp.I:
                read_bases_clipped += length
            else:
                remaining_length = length - remaining_to_clip
                read_bases_clipped += remaining_to_clip
                ref_bases_clipped += remaining_to_clip
                new_elems.append(CigarElement(remaining_length, op))
        else:
            read_bases_clipped += elem.length_on_query
            ref_bases_clipped += elem.length_on_target

    # Add in the remainder of the elements post-clipping
    new_elems.extend(elems)

    # Add in the clips
    clip_elems = []
    hard_clip_length = sum(map(lambda e: e.length, existing_hard_clips))
    soft_clip_length = sum(map(lambda e: e.length, existing_soft_clips)) + read_bases_clipped
    if hard_clip_length > 0:
        clip_elems.append(CigarElement(hard_clip_length, CigarOp.H))
    if soft_clip_length > 0:
        clip_elems.append(CigarElement(soft_clip_length, CigarOp.S))

    # Touch up the qualities if requested
    if clipped_base_quality is not None:
        for index in range(0, soft_clip_length):
            quals[index] = clipped_base_quality

    new_cigar = Cigar(tuple(clip_elems + new_elems))
    return new_cigar, ClippingInfo(read_bases_clipped, ref_bases_clipped)
