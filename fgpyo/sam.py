import attr
from typing import List
from samwell.sam import Cigar


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
        return ",".join(str(item) for item in attr.astuple(self, recurse=False))

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
