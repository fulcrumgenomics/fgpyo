from typing import Callable
from typing import List

from fgpyo.sam import Cigar
from fgpyo.sam import CigarElement
from fgpyo.sam import CigarOp


class Alignment:
    """
    A general class to describe the alignment between two sequences or partial ranges thereof
    """

    def __init__(
        self,
        query: str,
        target: str,
        query_start: int,
        target_start: int,
        cigar: Cigar,
        score: int,
    ):
        """
        Args:
            query: the query sequence
            target: the target sequence
            query_start: the 1-based position in the query sequence where the alignment begins
            target_start: the 1-based position in the target sequence where the alignment begins
            cigar: a Cigar object describing the alignment of the two sequences
            score: the alignment score
        """
        self.query: str = query
        self.target: str = target
        self.query_start: int = query_start
        self.target_start: int = target_start
        self.cigar: Cigar = cigar
        self.score: int = score

    @property
    def query_end(self) -> int:
        """
        Returns:
            One based closed coordinate of the end of the alignment on the query sequence.
        """
        return self.query_start + self.cigar.length_on_query() - 1

    @property
    def target_end(self) -> int:
        """
        Returns:
            One based closed coordinate of the end of the alignment on the target sequence.
        """
        return self.target_start + self.cigar.length_on_target() - 1

    def padded_string(
        self,
        match_char: str = "|",
        mismatch_char: str = ".",
        gap_char: str = " ",
        pad_char: str = "-",
    ) -> List[str]:
        """Generates a padded text representation of the alignment for visualization.
        The returned sequence will consist of three lines as follows (minus the labels on the left):

        query : ACGTGAACTGACT-ACTGTATGCG
        align : ||||| |||||| ||||||||.|
        target: ACGTG--CTGACTGACTGTATGGG

        Args:
            match_char: The character to use in the alignment line when the bases match.
            mismatch_char: The character to use in the alignment line when the bases mismatch.
            gap_char: The character to use in the alignment line when one of the
                sequences is gapped.
            pad_char: The character to use in the query or target sequence lines when
                padding is required.

        Returns:
            Three lines representing the alignment.
        """
        query_buffer = []
        align_buffer = []
        target_buffer = []

        q_offset = self.query_start - 1
        t_offset = self.target_start - 1

        for cig in self.cigar.elements:
            length = cig.length

            if cig.operator == CigarOp.I:
                for _ in range(length):
                    query_buffer.append(self.query[q_offset])
                    align_buffer.append(gap_char)
                    target_buffer.append(pad_char)
                    q_offset += 1
            elif cig.operator == CigarOp.D:
                for _ in range(length):
                    query_buffer.append(pad_char)
                    align_buffer.append(gap_char)
                    target_buffer.append(self.target[t_offset])
                    t_offset += 1
            else:
                for _ in range(length):
                    q = self.query[q_offset]
                    t = self.target[t_offset]
                    query_buffer.append(q)
                    target_buffer.append(t)

                    if cig.operator == CigarOp.EQ:
                        align_buffer.append(match_char)
                    elif cig.operator == CigarOp.X:
                        align_buffer.append(mismatch_char)
                    elif cig.operator == CigarOp.M:
                        align_buffer.append(match_char if q == t else mismatch_char)
                    else:
                        raise ValueError(f"Unsupported cigar operator: {cig.operator}")

                    q_offset += 1
                    t_offset += 1

        return ["".join(query_buffer), "".join(align_buffer), "".join(target_buffer)]

    def sub_by_query(self, start: int, end: int) -> "Alignment":
        """Returns a subset of the Alignment representing the region defined by start
        and end on the query sequence. The returned alignment will contain the entire
        query and target sequences, but will have adjusted query_start and target_start
        positions and an updated cigar. The score is set to 0.

        Args:
            start (int): The 1-based inclusive position of the first base on the query
                sequence to include.
            end (int): The 1-based inclusive position of the last base on the query
                sequence to include.

        Returns:
            A new Alignment with updated coordinates and cigar.
        """
        if not (
            self.query_start <= start <= self.query_end
            and self.query_start <= end <= self.query_end
        ):
            raise ValueError("start or end is outside of aligned region of target sequence")

        return self.sub(start, end, self.query_start, lambda elem: elem.operator.consumes_query)

    def sub_by_target(self, start: int, end: int) -> "Alignment":
        """Returns a subset of the Alignment representing the region defined by start and end on
        the target sequence. The returned alignment will contain the entire query and target
        sequences, but will have adjusted query_start and target_start positions and an updated
        cigar. The score is set to 0.

        Args:
            start (int): The 1-based inclusive position of the first base on the target sequence
                to include.
            end (int): The 1-based inclusive position of the last base on the target sequence
                to include.

        Returns:
            A new Alignment with updated coordinates and cigar.
        """
        if not (
            self.target_start <= start <= self.target_end
            and self.target_start <= end <= self.target_end
        ):
            raise ValueError("start or end is outside of aligned region of target sequence")

        return self.sub(
            start, end, self.target_start, lambda elem: elem.operator.consumes_reference
        )

    def sub(
        self, start: int, end: int, initial_start: int, consumes: Callable[[CigarElement], bool]
    ) -> "Alignment":
        """Private helper method that helps generate an Alignment that is a subset of the
        current alignment.

        Args:
            start: The start (on either the query or target sequence) of the desired window.
            end: The end (on either the query or target sequence) of the desired window.
            initial_start: The start position on the relevant sequence (either target OR query).
            consumes: A function that returns true if the cigar element passed
                as a parameter consumes
            bases on the sequence on which start and end are expressed.

        Returns:
            A new Alignment with adjusted start, end, and cigar, and with score=0.
        """
        elems = []
        q_start, t_start, curr_start = self.query_start, self.target_start, initial_start

        for elem in self.cigar.elements:
            element_consumes = consumes(elem)
            curr_end = curr_start + elem.length - 1 if element_consumes else curr_start - 1

            if curr_end < start:
                q_start += elem.length_on_query
                t_start += elem.length_on_target
                if element_consumes:
                    curr_start += elem.length
            elif curr_start > end:
                pass
            elif curr_start >= start and curr_end <= end:
                if element_consumes or curr_start != start:
                    elems.append(elem)
                    if element_consumes:
                        curr_start += elem.length
            else:
                length = elem.length

                if curr_start < start:
                    diff = start - curr_start
                    length -= diff
                    if elem.operator.consumes_query:
                        q_start += diff
                    if elem.operator.consumes_reference:
                        t_start += diff
                    curr_start += diff

                if curr_end > end:
                    length -= curr_end - end

                elems.append(CigarElement(length, elem.operator))
                curr_start += length

        return Alignment(
            query=self.query,
            target=self.target,
            query_start=q_start,
            target_start=t_start,
            cigar=Cigar(tuple(elems)),
            score=0,
        )
