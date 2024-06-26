from pathlib import Path
from typing import Optional

import pytest

from fgpyo.platform.illumina import IlluminaReadNumber
from fgpyo.platform.illumina import find_illumina_fastq


@pytest.mark.parametrize("fastq_ext", [".fq", ".fastq", ".fq.gz", ".fastq.gz"])
@pytest.mark.parametrize("read_number", IlluminaReadNumber)
@pytest.mark.parametrize("sample_number", ["S1", "S2", None])
@pytest.mark.parametrize("lane_number", ["L001", "L002", None])
@pytest.mark.parametrize("last_segment", ["001", None])
def test_find_illumina_fastq(
    tmp_path: Path,
    fastq_ext: str,
    read_number: IlluminaReadNumber,
    sample_number: Optional[str],
    lane_number: Optional[str],
    last_segment: Optional[str],
) -> None:
    """Test that we can find a FASTQ in the specified directory."""
    fastq_dir = tmp_path

    sample_name = "TestSample"

    # Build FASTQ file name
    fastq_fname = sample_name
    if sample_number is not None:
        fastq_fname += f"_{sample_number}"
    if lane_number is not None:
        fastq_fname += f"_{lane_number}"
    fastq_fname += f"_{read_number.value}"
    if last_segment is not None:
        fastq_fname += f"_{last_segment}"
    fastq_fname += fastq_ext

    expected_fastq_path = fastq_dir / fastq_fname
    expected_fastq_path.touch()

    actual_fastq_path = find_illumina_fastq(
        fastq_dir=fastq_dir, sample_id="TestSample", read_number=read_number
    )

    assert actual_fastq_path == expected_fastq_path


def test_find_illumina_fastq_raises_if_no_fastq(tmp_path: Path) -> None:
    """Should raise a ValueError if no FASTQ is found."""
    with pytest.raises(ValueError, match="No FASTQ found"):
        find_illumina_fastq(
            fastq_dir=tmp_path, sample_id="TestSample", read_number=IlluminaReadNumber.R1
        )


def test_find_illumina_fastq_raises_if_multiple_fastqs(tmp_path: Path) -> None:
    """Should raise a ValueError if multiple FASTQs are found."""
    (tmp_path / "TestSample_R1.fq").touch()
    (tmp_path / "TestSample_L001_R1.fq").touch()

    with pytest.raises(ValueError, match="More than one FASTQ found"):
        find_illumina_fastq(
            fastq_dir=tmp_path, sample_id="TestSample", read_number=IlluminaReadNumber.R1
        )


def test_find_illumina_fastq_can_find_recursively(tmp_path: Path) -> None:
    """Should be able to locate FASTQ files in subdirectories."""
    expected_fastq_path = tmp_path / "subdir" / "TestSample_R1.fq.gz"
    expected_fastq_path.parent.mkdir()
    expected_fastq_path.touch()

    actual_fastq_path = find_illumina_fastq(
        fastq_dir=tmp_path, sample_id="TestSample", read_number=IlluminaReadNumber.R1
    )

    assert actual_fastq_path == expected_fastq_path
