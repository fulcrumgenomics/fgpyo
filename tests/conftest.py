"""pytest configuration and shared fixtures."""

import pytest

try:
    import pysam  # noqa: F401

    HAS_PYSAM = True
except ImportError:
    HAS_PYSAM = False

requires_pysam = pytest.mark.skipif(not HAS_PYSAM, reason="pysam not installed")
"""Marker to skip tests that require pysam.

Usage:
    @requires_pysam
    def test_something_with_pysam():
        from fgpyo.sam import reader
        ...
"""
