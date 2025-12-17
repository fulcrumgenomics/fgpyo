"""Helpers for optional dependency imports."""

from types import ModuleType

_PYSAM_INSTALL_MSG = (
    "Missing optional dependency 'pysam'. "
    "The sam, vcf, fastx, and fasta modules require pysam. "
    "Install with: pip install fgpyo[pysam]"
)


def _get_pysam() -> ModuleType:
    """Import and return pysam, with a helpful error if not installed."""
    try:
        import pysam

        return pysam
    except ImportError as e:
        raise ImportError(_PYSAM_INSTALL_MSG) from e


def _check_pysam_installed() -> None:
    """Check if pysam is installed, raising ImportError if not."""
    try:
        import pysam  # noqa: F401
    except ImportError as e:
        raise ImportError(_PYSAM_INSTALL_MSG) from e
