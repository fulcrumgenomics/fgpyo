"""Basic tests for reference_set_builder"""

from pathlib import Path
from tempfile import NamedTemporaryFile as NamedTemp

import pytest
from py._path.local import LocalPath as TmpDir
from pytest import raises

from fgpyo.fasta.builder import FastaBuilder


def test_overrides_FastaBuilder() -> None:
    """Checks that defaults can be overriden in FastaBuilder"""
    builder = FastaBuilder(assembly="HG38", species="Human", line_length=90)
    assert builder.assembly == "HG38"
    assert builder.species == "Human"
    assert builder.line_length == 90


@pytest.mark.parametrize(
    "name, bases, times, length_bases",
    [
        ("chr1", "AAA", 3, 9),
        ("chr2", "TTT", 10, 30),
    ],
)
def test_bases_length_from_ContigBuilder_add(
    name: str,
    bases: str,
    times: int,
    length_bases: int,
) -> None:
    """Checks that the number of bases in each contig is correct"""
    builder = FastaBuilder()
    builder.add(name).add(bases, times)
    assert len(builder.__getitem__(name).bases) == length_bases


def test_override_existing_contig() -> None:
    """Asserts than an exception is raised when an override is attempted"""
    with raises(Exception):
        builder = FastaBuilder()
        builder.add("contig_name")
        builder.add("contig_name")


def test_contig_dict_is_not_accessable() -> None:
    """Ensures that an AttributeError is raised if FastaBuilder.__contig_builders is called"""
    builder = FastaBuilder()
    with raises(AttributeError):
        builder.__contig_builders["test"] = builder.add("chr10")


@pytest.mark.parametrize(
    "name, bases, times, expected",
    [
        ("chr3", "AAA a", 3, ("AAAA" * 3)),
        ("chr2", "TT T gT", 10, ("TTTGT" * 10)),
    ],
)
def test_bases_string_from_ContigBuilder_add(
    name: str,
    bases: str,
    times: int,
    expected: str,
    tmpdir: TmpDir,
) -> None:
    """
    Reads bases back from fasta and checks that extra spaces are removed and bases are uppercase
    """
    builder = FastaBuilder()
    builder.add(name).add(bases, times)
    with NamedTemp(suffix=".fa", dir=tmpdir, mode="w", delete=True) as fp:
        builder.to_file(Path(fp.name))
        with open(fp.name, "r") as read_fp:
            for line in read_fp.readlines():
                if ">" not in line:
                    assert line.strip() == expected
