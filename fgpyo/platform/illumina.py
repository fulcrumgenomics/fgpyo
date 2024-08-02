"""
Methods for working with Illumina-specific UMIs in SAM files
------------------------------------

The functions in this module make it easy to:

* check whether a UMI is valid
* extract UMI(s) from an Illumina-style read name
* copy a UMI from an alignment's read name to its `RX` SAM tag

"""

from typing import Optional
from typing import Set

from pysam import AlignedSegment

SAM_UMI_DELIMITER: str = "-"
"""Multiple UMI delimiter, which SAM specification recommends should be a hyphen;
see specification here: https://samtools.github.io/hts-specs/SAMtags.pdf"""

_VALID_UMI_CHARACTERS: Set[str] = set("ACGTN")
"""Illumina's restricted UMI characters;
https://support.illumina.com/help/BaseSpace_Sequence_Hub_OLH_009008_2/Source/Informatics/BS/FileFormat_FASTQ-files_swBS.htm."""  # noqa

_ILLUMINA_UMI_DELIMITER: str = "+"
"""Multiple UMIs are delimited with a plus-sign in Illumina FASTQs; see docs above."""

_ILLUMINA_READ_NAME_DELIMITER: str = ":"
"""Illumina read names are delimited with a colon."""


def extract_umis_from_read_name(
    read_name: str,
    read_name_delimiter: str = _ILLUMINA_READ_NAME_DELIMITER,
    umi_delimiter: str = _ILLUMINA_UMI_DELIMITER,
    strict: bool = False,
) -> Optional[str]:
    """Extract UMI(s) from an Illumina-style read name.

    The UMI is expected to be the final component of the read name, delimited by the
    `read_name_delimiter`. Multiple UMIs may be present, delimited by the `umi_delimiter`. This
    delimiter will be replaced by the SAM-standard `-`.

    Args:
        read_name: The read name to extract the UMI from.
        read_name_delimiter: The delimiter separating the components of the read name.
        umi_delimiter: The delimiter separating multiple UMIs.
        strict: If `strict` is `True`, the read name must contain either 7 or 8 colon-separated
            segments. The UMI is assumed to be the last one in the case of 8 segments and `None`
            in the case of 7 segments. `strict` requires the UMI to be valid and consistent with
            Illumina's allowed UMI characters. If `strict` is `False`, the last segment is returned
            so long as it appears to be a valid UMI.

    Returns:
        The UMI extracted from the read name, or None if no UMI was found. Multiple UMIs are
        returned in a single string, separated by a hyphen (`-`).

    Raises:
        ValueError: If the read name does not end with a valid UMI.
    """
    if strict:
        colons = read_name.count(":")
        if colons == 6:  # number of fields is 7
            return None
        elif colons != 7:
            raise ValueError(
                f"Trying to extract UMIs from read with {colons + 1} parts "
                f"(7 or 8 expected): {read_name}"
            )
    raw_umi = read_name.split(read_name_delimiter)[-1]
    # Check each UMI individually
    umis = raw_umi.split(umi_delimiter)
    # Strip the "r" from rev-comped UMIs
    # (NB: for consistency with UMI_tools, the UMI is not revcomped)
    umis = [umi.lstrip("r") for umi in umis]

    invalid_umis = [umi for umi in umis if not _is_valid_umi(umi)]
    if len(invalid_umis) == 0:
        return SAM_UMI_DELIMITER.join(umis)
    elif strict:
        raise ValueError(
            f"Invalid UMIs found in read name: {read_name}",
            f"  (Invalid UMIs: {', '.join(invalid_umis)})",
        )
    else:
        return None


def copy_umi_from_read_name(
    rec: AlignedSegment, strict: bool = False, remove_umi: bool = False
) -> bool:
    """
    Copy a UMI from an alignment's read name to its `RX` SAM tag. UMI will not be copied to RX
    tag if invalid.

    Args:
        rec: The alignment record to update.
        strict: If `True` and UMI invalid, will throw an exception
        remove_umi: If `True`, the UMI will be removed from the read name after copying.

    Returns:
        `True` if the UMI was successfully extracted, False if otherwise.

    Raises:
        ValueError: If the read name does not end with a valid UMI.
        ValueError: If the record already has a populated `RX` SAM tag.
    """

    umi = extract_umis_from_read_name(
        read_name=rec.query_name,
        strict=strict,
        umi_delimiter=_ILLUMINA_READ_NAME_DELIMITER,
    )
    if umi is not None:
        if rec.has_tag("RX"):
            raise ValueError(f"Record {rec.query_name} already has a populated RX tag")
        rec.set_tag(tag="RX", value=umi)
        if remove_umi:
            last_index = rec.query_name.rfind(_ILLUMINA_READ_NAME_DELIMITER)
            rec.query_name = rec.query_name[:last_index] if last_index != -1 else rec.query_name
        return True
    elif strict:
        raise ValueError(f"Invalid UMI {umi} extracted from {rec.query_name}")
    else:
        return False


def _is_valid_umi(umi: str) -> bool:
    """Check whether a UMI is valid.
    Illumina UMIs may only contain A/C/G/T/N.
    https://support.illumina.com/help/BaseSpace_Sequence_Hub_OLH_009008_2/Source/Informatics/BS/FileFormat_FASTQ-files_swBS.htm
    Args:
        umi: The UMI to check.
    Returns:
        `True` if the UMI is valid, `False` otherwise.
    """

    return len(umi) > 0 and set(umi).issubset(_VALID_UMI_CHARACTERS)
