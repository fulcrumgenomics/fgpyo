"""
Classes for generating fasta files and records for testing
----------------------------------------------------------
This module contains utility classes for creating fasta files, indexed fasta files (.fai), and
sequence dictionaries (.dict).

Examples of creating sets of contigs for writing to fasta
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Writing a FASTA with two contigs each with 100 bases.
.. code-block:: python
    >>> from fgpyo.fasta.builder import FastaBuilder
    >>> builder = FastaBuilder()
    >>> builder.add("chr10").add("AAAAAAAAAA", 10)
    >>> builder.add("chr11").add("GGGGGGGGGG", 10)
    >>> builder.to_file(path = pathlib.Path("test.fasta"))
Writing a FASTA with one contig with 100 A's and 50 T's
    >>> from fgpyo.fasta.builder import FastaBuilder
    >>> builder = FastaBuilder()
    >>> builder.add("chr10").add("AAAAAAAAAA", 10).add("TTTTTTTTTT", 5)
    >>> builder.to_file(path = pathlib.Path("test.fasta"))
Add bases to existing contig
    >>> from fgpyo.fasta.builder import FastaBuilder
    >>> builder = FastaBuilder()
    >>> contig_one = builder.add("chr10").add("AAAAAAAAAA", 1)
    >>> contig_one.add("NNN", 1)
    >>> contig_one.bases
    'AAAAAAAAAANNN'
"""
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Optional

""" Stubs for pysam imports """
if TYPE_CHECKING:

    def samtools_dict(*args: Any) -> None:
        pass

    def samtools_faidx(*args: Any) -> None:
        pass


else:
    from pysam import dict as samtools_dict
    from pysam import faidx as samtools_faidx


def pysam_dict(assembly: str, species: str, output_path: str, input_path: str) -> None:
    """Calls pysam.dict and writes the sequence dictionary to the provided output path

    Args
        assembly: Assembly
        species: Species
        output_path: File path to write dictionary to
        input_path: Path to fasta file
    """
    samtools_dict("-a", assembly, "-s", species, "-o", output_path, input_path)


def pysam_faidx(input_path: str) -> None:
    """Calls pysam.faidx and writes fasta index in the same file location as the fasta file

    Args
        input_path: Path to fasta file
    """
    samtools_faidx(input_path)


class ContigBuilder:
    """Builder for constructing new contigs, and adding bases to existing contigs.
    Existing contigs cannot be overwritten, each contig name in FastaBuilder must
    be unique. Instances of ContigBuilders should be created using FastaBuilder.add(),
    where species and assembly are optional parameters and will defualt to
    FastaBuilder.assembly and FastaBuilder.species.

    Attributes:
        name: Unique contig ID, ie., "chr10"
        assembly: Assembly information, if None default is 'testassembly'
        species: Species information, if None default is 'testspecies'
        bases:  The bases to be added to the contig ex "A"

    """

    def __init__(
        self,
        name: str,
        assembly: str,
        species: str,
    ):
        self.name = name
        self.assembly = assembly
        self.species = species
        self.bases = ""

    def add(self, bases: str, times: int) -> "ContigBuilder":
        """
        Method for adding bases to a new or existing instance of ContigBuilder.

        Args:
            bases: The bases to be added to the contig
            times: The number of times the bases should be repeated

        Example
        add("AAA", 2) results in the following bases -> "AAAAAA"
        """
        # Remove any spaces in string and enforce upper case format
        bases = bases.replace(" ", "").upper()
        self.bases += str(bases * times)
        return self


class FastaBuilder:
    """Builder for constructing sets of one or more contigs.

    Provides the ability to manufacture sets of contigs from minimal input, and automatically
    generates the information necessary for writing the FASTA file, index, and dictionary.

    A builder is constructed from an assembly, species, and line length. All attributes have
    defaults, however these can be overwritten.

    Contigs are added to FastaBuilder using:
    :func:`~fgpyo.fasta.builder.FastaBuilder.add`

    Bases are added to existing contigs using:
    :func:`~fgpyo.fasta.builder.FastaBuilder.add.add`

    Once accumulated the contigs can be written to a file using:
    :func:`~fgpyo.fasta.builder.FastaBuilder.to_file`

    Calling to_file() will also generate the fasta index (.fai) and sequence dictionary (.dict).

    Attributes:
        assembly: Assembly information, if None default is 'testassembly'
        species: Species, if None default is 'testspecies'
        line_length: Desired line length, if None default is 80
        contig_builders: Private dictionary of contig names and instances of ContigBuilder
    """

    def __init__(
        self,
        assembly: str = "testassembly",
        species: str = "testspecies",
        line_length: int = 80,
    ):
        self.assembly: str = assembly
        self.species: str = species
        self.line_length: int = line_length
        self.__contig_builders: Dict[str, ContigBuilder] = {}

    def __getitem__(self, key: str) -> ContigBuilder:
        """ Access instance of ContigBuilder by name """
        return self.__contig_builders[key]

    def add(
        self,
        name: str,
        assembly: Optional[str] = None,
        species: Optional[str] = None,
    ) -> ContigBuilder:
        """
        Creates and returns a new ContigBuilder for a contig with the provided name.
        Contig names must be unique, attempting to create two seperate contigs with the same
        name will result in an error.

        Args:
            name: Unique contig ID, ie., "chr10"
            assembly: Assembly information, if None default is 'testassembly'
            species: Species information, if None default is 'testspecies'
        """
        # Asign self.species and self.assembly to assembly and species if parameter is None
        assembly = assembly if assembly is not None else self.assembly
        species = species if species is not None else self.species

        # Assert that the provided name does not already exist
        assert name not in self.__contig_builders, (
            f"The contig {name} already exists, see docstring for methods on "
            f"adding bases to existing contigs"
        )
        builder: ContigBuilder = ContigBuilder(name=name, assembly=assembly, species=species)
        self.__contig_builders[name] = builder
        return builder

    def to_file(
        self,
        path: Path,
    ) -> None:
        """
        Writes out the set of accumulated contigs to a FASTA file at the `path` given.
        Also generates the accompanying fasta index file (`.fa.fai`) and sequence
        dictionary file (`.dict`).

        Contigs are emitted in the order they were added to the builder.  Sequence
        lines in the FASTA file are wrapped to the line length given when the builder
        was constructed.

        Args:
            path: Path to write files to.

        Example:
        FastaBuilder.to_file(path = pathlib.Path("my_fasta.fa"))
        """

        with path.open("w") as writer:
            for contig in self.__contig_builders.values():
                try:
                    writer.write(f">{contig.name}")
                    writer.write("\n")
                    for line in textwrap.wrap(contig.bases, self.line_length):
                        writer.write(line)
                        writer.write("\n")
                except OSError as error:
                    raise Exception(f"Could not write to {writer}") from error

        # Index fasta
        pysam_faidx(str(path))

        # Write dictionary
        pysam_dict(
            assembly=self.assembly,
            species=self.species,
            output_path=str(f"{path}.dict"),
            input_path=str(path),
        )
