"""
Alignment records for a sequenced template
------------------------------------------

Container holding all read alignments corresponding to a sequenced template, including secondary
and supplementary alignments

Example of iterating through a SAM/BAM file and yielding complete templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python
   >>> from pysam import AlignmentFile
   >>> from fgpyo.template import Template
   >>> bam_reader: AlignmentFile = AlignmentFile("alignments.bam")
   >>> templates: List[Template] = [t for t in Template.to_templates(bam_reader.fetch())]
"""
from typing import Iterable, Iterator, List

import attr
from pysam import AlignedSegment


@attr.s(auto_attribs=True, frozen=True)
class Template:
    """A container for alignment records corresponding to a single sequenced template.

    Attributes:
        r1: Primary alignment for read 1, or None if there is none
        r2: Primary alignment for read 2, or None if there is none
        r1_supplementals: Supplementary alignments for read 1
        r2_supplementals: Supplementary alignments for read 2
        r1_secondaries: Secondary (non-primary) alignments for read 1
        r2_secondaries: Secondary (non-primary) alignments for read 2
    """

    r1: AlignedSegment = None
    r2: AlignedSegment = None
    r1_supplementals: Iterable[AlignedSegment] = ()  # Immutable
    r2_supplementals: Iterable[AlignedSegment] = ()
    r1_secondaries: Iterable[AlignedSegment] = ()
    r2_secondaries: Iterable[AlignedSegment] = ()

    @staticmethod
    def to_templates(alignments: Iterable[AlignedSegment]) -> Iterator["Template"]:
        """Returns an iterator over full templates. Assumes the input iterable is queryname-sorted,
        and gathers contiguous sequences of records sharing a common query name into templates."""
        curr_qname: str = ""
        curr_recs: List[AlignedSegment] = []
        for rec in alignments:
            if rec.query_name == curr_qname:
                curr_recs.append(rec)
            else:
                if len(curr_recs) > 0:
                    yield Template._to_template(curr_recs)
                curr_qname = rec.query_name
                curr_recs = []
        if curr_recs:
            yield Template._to_template(curr_recs)

    @staticmethod
    def _to_template(recs: Iterable[AlignedSegment]) -> "Template":
        r1 = None
        r2 = None
        r1_supplementals: List[AlignedSegment] = []
        r2_supplementals: List[AlignedSegment] = []
        r1_secondaries: List[AlignedSegment] = []
        r2_secondaries: List[AlignedSegment] = []
        for rec in recs:
            if not rec.is_supplementary and not rec.is_secondary:
                if rec.is_read1 or not rec.is_paired:
                    r1 = rec
                else:
                    r2 = rec
            if rec.is_supplementary:
                if rec.is_read1 or not rec.is_paired:
                    r1_supplementals.append(rec)
                else:
                    r2_supplementals.append(rec)
            if rec.is_secondary:
                if rec.is_read1 or not rec.is_paired:
                    r1_secondaries.append(rec)
                else:
                    r2_secondaries.append(rec)
        return Template(
            r1=r1,
            r2=r2,
            r1_supplementals=r1_supplementals,
            r2_supplementals=r2_supplementals,
            r1_secondaries=r1_secondaries,
            r2_secondaries=r2_secondaries,
        )
