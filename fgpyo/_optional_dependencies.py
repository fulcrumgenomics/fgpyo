try:
    import pysam  # noqa: F401

    HAS_PYSAM = True
except ImportError:
    HAS_PYSAM = False


def require_pysam() -> None:
    if not HAS_PYSAM:
        raise ImportError(
            "This functionality requires pysam. Install with: pip install fgpyo[pysam]"
        )
