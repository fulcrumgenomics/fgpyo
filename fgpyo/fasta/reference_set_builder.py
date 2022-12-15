"""
Classes for generating Fasta files and records for testing
----------------------------------------------------------------
"""

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

# pylint: disable=W0511


class ReferenceSetBuilder:
    """
    Builder for constructing one or more fasta records.
    """

    # The default asssembly
    DEFAULT_ASSEMBLY: str = "testassembly"

    # The default species
    DEFAULT_SPECIES: str = "testspecies"

    # Way to store instance of ReferenceBuilder
    # TODO make something better than a list... probably
    REF_BUILDERS = []

    def __init__(
        self,
        assembly: Optional[str] = None,
        species: Optional[str] = None,
        line_length: int = 80,
    ):
        self.assembly: str = assembly if assembly is not None else self.DEFAULT_ASSEMBLY
        self.species: str = species if species is not None else self.DEFAULT_SPECIES
        self.line_length = line_length

    def add(
        self,
        name: str,
    ):
        """
        Returns instance of ReferenceBuilder
        """
        builder = _ReferenceBuilder(
            name=name, assembly=self.assembly, species=self.species
        )
        self.REF_BUILDERS.append(builder)
        return self.REF_BUILDERS[-1]

    def to_temp_file(
        self,
        delete_on_exit: Optional[bool] = None,
        calculate_md5_sum: Optional[bool] = None,
    ):
        """
        For each instance of ReferenceBuilder in REF_BUILDERS write record to fasta temp
        """
        # Set defaults
        delete_on_exit: bool = delete_on_exit if delete_on_exit is not None else True
        calculate_md5_sum: bool = (
            calculate_md5_sum if calculate_md5_sum is not None else False
        )

        # Write temp file path
        path_to_fasta = NamedTemporaryFile(
            prefix=f"{self.assembly}_{self.species}", suffix=".fasta"
        )

        # Refactor...
        for record in enumerate(self.REF_BUILDERS):
            seq = self.REF_BUILDERS[record].sequences
            assembly = self.REF_BUILDERS[record].assembly
            species = self.REF_BUILDERS[record].species
            name = self.REF_BUILDERS[record].name
            header = f">{name}[{assembly}][{species}]\n"
            # Add newline to seq every self.line_length
            # write to path_to_fasta
            # call helper for writing dict and fai

    def to_file(
        self,
        paht: Path,
        delete_on_exit: Optional[bool] = None,
        calculate_md5_sum: Optional[bool] = None,
    ):
        """
        Same as to_temp_file() but user provides path
        """


# pylint: disable=R0903
class _ReferenceBuilder:
    """
    Creates individiaul records
    """

    def __init__(
        self,
        name: str,
        assembly: str,
        species: str,
        sequences: Optional[str] = None,
    ):
        self.name = name
        self.assembly = assembly
        self.species = species
        self.sequences = sequences

    def add(self, seq: str, times: int) -> None:
        """
        "AAA"*3 = AAAAAAAAA
        """
        self.sequences = seq * times


### Scratch ###
builder_ex = ReferenceSetBuilder()
builder_ex.add("chr10").add("NNNNNNNNNN", 10)
builder_ex.add("chr1").add("AAAAAAAAAA", 10)
builder_ex.add("chr3").add("GGGGGGGGGG", 10)
builder_ex.to_temp_file()
