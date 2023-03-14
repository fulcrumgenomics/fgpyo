import logging
import pytest
import pysam


from fgpyo.util.logging import ProgressLogger
from fgpyo.sam.builder import SamBuilder
from fgpyo import sam

CHROM = "ACGCTAGACTGCTAGCAGCATCTCATAGCACTTCGCGCTATAGCGATATAAATATCGCGATCTAGCG"

def test_progress_logger() -> None:
    logger = logging.getLogger(__name__)
    progress: ProgressLogger = ProgressLogger(printer=logger, noun="noun", verb="verb", unit=3)
    assert not progress.record()
    assert not progress.record()
    assert progress.record()
    assert not progress.log_last()  # since it was logged
    assert not progress.record()
    assert progress.log_last()  # since it hasn't been logged


def test_progress_logger_with_custom_printer() -> None:
    ss = []
    progress = ProgressLogger(printer=lambda s: ss.append(s), noun="things", verb="saw", unit=2)
    for i in range(0, 4):
        progress.record()

    assert ss == ["saw 2 things: NA", "saw 4 things: NA"]


def test_progress_logger_as_context_manager() -> None:
    ss = []
    with ProgressLogger(printer=lambda s: ss.append(s), noun="xs", verb="saw", unit=9) as progress:
        for i in range(0, 7):
            progress.record()

    assert ss == ["saw 7 xs: NA"]

builder = SamBuilder()
record_mapped = builder.add_single(bases=CHROM[10:40], chrom="chr1", start=10, cigar="30M")
r1_unmapped_v1, r2_unmapped_v1 = builder.add_pair(chrom="chr1", start1=1000)
r1_unmapped_v2, r2_unmapped_v2 = builder.add_pair(chrom=sam.NO_REF_NAME)
@pytest.mark.parametrize(
    "record",
    [
        (record_mapped),
        (r2_unmapped_v1),
        (r2_unmapped_v2),
    ],
)
def test_record_alignment_mapped_record(record: pysam.AlignedSegment) -> None:
    # Define instance of ProgressLogger
    rr = []
    progress = ProgressLogger(printer=lambda r: rr.append(r), noun="record(s)", verb="recorded", unit=1)

    # Assert record is logged
    assert(progress.record_alignment(rec = record) is True)
 

