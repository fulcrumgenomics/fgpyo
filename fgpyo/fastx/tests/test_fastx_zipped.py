import gzip
from pathlib import Path

import pytest

from fgpyo.fastx import FastxZipped

# TODO: Remove all the assert boilerplate when FastxRecord can be used for equality testing:
#       https://github.com/pysam-developers/pysam/issues/1243


def test_fastx_zipped_requires_at_least_one_fastx() -> None:
    """Test that :class:`FastxZipped` requires at least one FASTX path to be instantiated."""
    with pytest.raises(ValueError, match=r"Must provide at least one FASTX"):
        FastxZipped()


def test_fastx_zipped_iterates_one_empty_fastx(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` can iterate over one empty FASTX file."""
    input = tmp_path / "input"
    input.mkdir()
    fastx = input / "input.fastx"
    fastx.write_text("")

    with FastxZipped(fastx) as handle:
        assert len(list(handle)) == 0


def test_fastx_zipped_iterates_over_a_single_fasta(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` can iterate over a single FASTA file."""
    input = tmp_path / "input"
    input.mkdir()
    fasta = input / "input.fasta"
    fasta.write_text(">seq1\nACGT\n>seq2\nTGCA\n")

    context_manager = FastxZipped(fasta)
    with context_manager as handle:
        (record1,) = next(handle)
        assert record1.name == "seq1"
        assert record1.sequence == "ACGT"
        (record2,) = next(handle)
        assert record2.name == "seq2"
        assert record2.sequence == "TGCA"

    assert all(fastx.closed for fastx in context_manager._fastx)


def test_fastx_zipped_iterates_over_a_single_fasta_gzipped(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` can iterate over a single gzipped FASTA file."""
    input = tmp_path / "input"
    input.mkdir()
    fasta = input / "input.fasta.gz"

    with gzip.open(fasta, "wt") as handle:
        handle.write(">seq1\nACGT\n>seq2\nTGCA\n")

    context_manager = FastxZipped(fasta)
    with context_manager as handle:
        (record1,) = next(handle)
        assert record1.name == "seq1"
        assert record1.sequence == "ACGT"
        (record2,) = next(handle)
        assert record2.name == "seq2"
        assert record2.sequence == "TGCA"

    assert all(fastx.closed for fastx in context_manager._fastx)


def test_fastx_zipped_iterates_over_a_single_fastq(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` can iterate over a single FASTQ file."""
    input = tmp_path / "input"
    input.mkdir()
    fastq = input / "input.fastq"
    fastq.write_text("@seq1\tcomment1\nACGT\n+\nFFFF\n" + "@seq2\tcomment2\nTGCA\n+\n!!!!\n")

    context_manager = FastxZipped(fastq)
    with context_manager as handle:
        (record1,) = next(handle)
        assert record1.name == "seq1"
        assert record1.sequence == "ACGT"
        assert record1.comment == "comment1"
        assert record1.quality == "FFFF"
        (record2,) = next(handle)
        assert record2.name == "seq2"
        assert record2.sequence == "TGCA"
        assert record2.comment == "comment2"
        assert record2.quality == "!!!!"

    assert all(fastx.closed for fastx in context_manager._fastx)


def tests_fastx_zipped_raises_exception_on_truncated_fastx(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` raises an exception on truncated FASTX files."""
    input = tmp_path / "input"
    input.mkdir()
    fasta1 = input / "input1.fasta"
    fasta2 = input / "input2.fasta"
    fasta1.write_text(">seq1\nAAAA\n")
    fasta2.write_text(">seq1\nCCCC\n>seq2\nGGGG\n")

    context_manager = FastxZipped(fasta1, fasta2)
    with context_manager as handle:
        (record1, record2) = next(handle)
        assert record1.name == "seq1"
        assert record1.sequence == "AAAA"
        assert record2.name == "seq1"
        assert record2.sequence == "CCCC"
        with pytest.raises(ValueError, match=r"One or more of the FASTX files is truncated.*"):
            next(handle)

    assert all(fastx.closed for fastx in context_manager._fastx)

    context_manager = FastxZipped(fasta2, fasta1)
    with context_manager as handle:
        (record1, record2) = next(handle)
        assert record1.name == "seq1"
        assert record1.sequence == "CCCC"
        assert record2.name == "seq1"
        assert record2.sequence == "AAAA"
        with pytest.raises(ValueError, match=r"One or more of the FASTX files is truncated.*"):
            next(handle)

    assert all(fastx.closed for fastx in context_manager._fastx)


def tests_fastx_zipped_can_iterate_over_multiple_fastx_files(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` can iterate over multiple FASTX files."""
    input = tmp_path / "input"
    input.mkdir()
    fasta1 = input / "input1.fasta"
    fasta2 = input / "input2.fasta"
    fasta1.write_text(">seq1\nAAAA\n>seq2\nCCCC\n")
    fasta2.write_text(">seq1\nGGGG\n>seq2\nTTTT\n")

    context_manager = FastxZipped(fasta1, fasta2)
    with context_manager as handle:
        (record1, record2) = next(handle)
        assert record1.name == "seq1"
        assert record1.sequence == "AAAA"
        assert record2.name == "seq1"
        assert record2.sequence == "GGGG"
        (record1, record2) = next(handle)
        assert record1.name == "seq2"
        assert record1.sequence == "CCCC"
        assert record2.name == "seq2"
        assert record2.sequence == "TTTT"

    assert all(fastx.closed for fastx in context_manager._fastx)


def tests_fastx_zipped_raises_exception_on_mismatched_sequence_names(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` raises an exception on mismatched sequence names."""
    input = tmp_path / "input"
    input.mkdir()
    fasta1 = input / "input1.fasta"
    fasta2 = input / "input2.fasta"
    fasta1.write_text(">seq1\nAAAA\n")
    fasta2.write_text(">seq2\nCCCC\n")

    context_manager = FastxZipped(fasta1, fasta2)
    with context_manager as handle:
        with pytest.raises(ValueError, match=r"FASTX record names do not all match"):
            next(handle)

    assert all(fastx.closed for fastx in context_manager._fastx)


def tests_fastx_zipped_handles_sequence_names_with_suffixes(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` does not use sequence name suffixes in equality tests."""
    input = tmp_path / "input"
    input.mkdir()
    fasta1 = input / "input1.fasta"
    fasta2 = input / "input2.fasta"
    fasta1.write_text(">seq1/1\nAAAA\n")
    fasta2.write_text(">seq1/2\nCCCC\n")

    context_manager = FastxZipped(fasta1, fasta2)
    with context_manager as handle:
        (record1, record2) = next(handle)
        assert record1.name == "seq1/1"
        assert record1.sequence == "AAAA"
        assert record2.name == "seq1/2"
        assert record2.sequence == "CCCC"

    assert all(fastx.closed for fastx in context_manager._fastx)


def tests_fastx_zipped__name_minus_ordinal_works_with_r1_and_r2_ordinals() -> None:
    """Test that :class:`FastxZipped._name_minus_ordinal` works with none, R1, and R2 ordinals."""
    assert FastxZipped._name_minus_ordinal("") == ""
    assert FastxZipped._name_minus_ordinal("/1") == ""
    assert FastxZipped._name_minus_ordinal("/2") == ""
    assert FastxZipped._name_minus_ordinal("seq1") == "seq1"
    assert FastxZipped._name_minus_ordinal("seq1/1") == "seq1"
    assert FastxZipped._name_minus_ordinal("seq1/2") == "seq1"
    assert FastxZipped._name_minus_ordinal("1") == "1"
    assert FastxZipped._name_minus_ordinal("1/1") == "1"
    assert FastxZipped._name_minus_ordinal("1/2") == "1"


def test_fastx_zipped_accidentally_used_as_iterator_only(tmp_path: Path) -> None:
    """Test that :class:`FastxZipped` can also be used as an interator outside a context manager."""
    input = tmp_path / "input"
    input.mkdir()
    fasta1 = input / "input1.fasta"
    fasta2 = input / "input2.fasta"
    fasta1.write_text(">seq1\nAAAA\n>seq2\nCCCC\n")
    fasta2.write_text(">seq1\nGGGG\n>seq2\nTTTT\n")

    zipped = FastxZipped(fasta1, fasta2)
    (record1, record2) = next(zipped)
    assert record1.name == "seq1"
    assert record1.sequence == "AAAA"
    assert record2.name == "seq1"
    assert record2.sequence == "GGGG"
    (record1, record2) = next(zipped)
    assert record1.name == "seq2"
    assert record1.sequence == "CCCC"
    assert record2.name == "seq2"
    assert record2.sequence == "TTTT"

    with pytest.raises(StopIteration):
        next(zipped)

    assert all(not fastx.closed for fastx in zipped._fastx)
    zipped.close()
    assert all(fastx.closed for fastx in zipped._fastx)
