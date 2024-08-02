from enum import Enum
from enum import unique
from glob import glob
from pathlib import Path
from typing import List


@unique
class IlluminaReadNumber(Enum):
    """The read number of an Illumina FASTQ."""

    R1 = "R1"
    R2 = "R2"
    I1 = "I1"
    I2 = "I2"


FASTQ_EXTENSIONS = [".fq", ".fastq", ".fq.gz", ".fastq.gz"]


def find_illumina_fastq(
    fastq_dir: Path,
    sample_id: str,
    read_number: IlluminaReadNumber,
    recursive: bool = True,
) -> Path:
    """
    Search a directory for a FASTQ belonging to the specified sample.

    The function will search for a FASTQ prefixed with `sample_id`, including the specified
    `read_number`, and suffixed with `.fastq`, `.fq`, `.fastq.gz`, or `.fq.gz`.

    Args:
        fastq_dir: The directory to search.
        sample_id: The sample ID. The function will search for a FASTQ prefixed with this string.
        read_number: The read number.
        recursive: If True, search subdirectories.

    Returns:
        The path to the discovered FASTQ file.

    Raises:
        ValueError: If no FASTQ is found.
        ValueError: If more than one FASTQ is found.
    """
    fastqs: List[str] = []
    for fastq_ext in FASTQ_EXTENSIONS:
        if recursive:
            glob_pattern = f"{fastq_dir}/**/{sample_id}*{read_number.value}*{fastq_ext}"
        else:
            glob_pattern = f"{fastq_dir}/{sample_id}*{read_number.value}*{fastq_ext}"

        fastqs.extend(glob(glob_pattern, recursive=recursive))

    if len(fastqs) == 0:
        raise ValueError(
            f"No FASTQ found for sample ID '{sample_id}' and read number '{read_number.value}'"
        )
    if len(fastqs) > 1:
        raise ValueError(
            f"More than one FASTQ found for sample ID '{sample_id}' and "
            f"read number '{read_number.value}'"
        )

    return Path(fastqs[0])
