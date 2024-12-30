import logging

import pysam
import pytest

from fgpyo import sam
from fgpyo.sam import Template
from fgpyo.sam.builder import SamBuilder
from fgpyo.util.logging import ProgressLogger


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
    for _ in range(0, 4):
        progress.record()

    assert ss == ["saw 2 things: NA", "saw 4 things: NA"]


def test_progress_logger_as_context_manager() -> None:
    ss = []
    with ProgressLogger(printer=lambda s: ss.append(s), noun="xs", verb="saw", unit=9) as progress:
        for _ in range(0, 7):
            progress.record()

    assert ss == ["saw 7 xs: NA"]


builder = SamBuilder()
r1_mapped_named, r2_unmapped_named = builder.add_pair(chrom="chr1", start1=1000)
r1_unmapped_un_named, r2_unmapped_un_named = builder.add_pair(chrom=sam.NO_REF_NAME)


@pytest.mark.parametrize(
    "record",
    [
        (r1_mapped_named),
        (r2_unmapped_named),
        (r2_unmapped_un_named),
    ],
)
def test_record_alignment_mapped_record(record: pysam.AlignedSegment) -> None:
    # Define instance of ProgressLogger
    rr = []
    progress = ProgressLogger(
        printer=lambda r: rr.append(r), noun="record(s)", verb="recorded", unit=1
    )

    # Assert record is logged
    assert progress.record_alignment(rec=record) is True


def test_record_multiple_alignments() -> None:
    builder: SamBuilder = SamBuilder()
    (r1, r2) = builder.add_pair(name="x", chrom="chr1", start1=1, start2=2)
    (r1_secondary, r2_secondary) = builder.add_pair(name="x", chrom="chr1", start1=10, start2=12)
    r1_secondary.is_secondary = True
    r2_secondary.is_secondary = True
    (r1_supplementary, r2_supplementary) = builder.add_pair(
        name="x", chrom="chr1", start1=4, start2=6
    )
    r1_supplementary.is_supplementary = True
    r2_supplementary.is_supplementary = True

    template = Template.build(builder.to_unsorted_list())
    expected = Template(
        name="x",
        r1=r1,
        r2=r2,
        r1_secondaries=[r1_secondary],
        r2_secondaries=[r2_secondary],
        r1_supplementals=[r1_supplementary],
        r2_supplementals=[r2_supplementary],
    )

    assert template == expected

    # Define instance of ProgressLogger
    actual: list[str] = []

    progress = ProgressLogger(
        printer=lambda rec: actual.append(rec), noun="record(s)", verb="recorded", unit=1
    )

    # Assert record is logged
    assert progress.record_alignments(recs=template.all_recs()) is True

    # Assert every record was logged
    assert len(actual) == 6
