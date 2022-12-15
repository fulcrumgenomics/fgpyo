"""
Classes for generating Fasta files and records for testing
----------------------------------------------------------
"""
# import hashlib
import os
import textwrap
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import ClassVar
from typing import List
from typing import Optional


class ReferenceSetBuilder:
    """
    Builder for constructing one or more fasta records.

    Parameters:
    assembly (str):

    species (str):

    line_length (str):
    """

    # The default asssembly
    DEFAULT_ASSEMBLY: ClassVar[str] = "testassembly"

    # The default species
    DEFAULT_SPECIES: ClassVar[str] = "testspecies"

    # Way to store instance of ReferenceBuilder
    REF_BUILDERS: List["ReferenceBuilder"] = []

    def __init__(
        self,
        assembly: str = DEFAULT_ASSEMBLY,
        species: str = DEFAULT_SPECIES,
        line_length: int = 80,
    ):
        self.assembly: str = assembly
        self.species: str = species
        self.line_length: int = line_length

    def add(
        self,
        name: str,
    ) -> "ReferenceBuilder":
        """
        Returns instance of ReferenceBuilder
        """

        builder: ReferenceBuilder = ReferenceBuilder(
            name=name, assembly=self.assembly, species=self.species
        )
        self.REF_BUILDERS.append(builder)
        return builder

    def writer_helper(
        self,
    ) -> None:
        """ Place holder for helper function """
        return None

    def to_temp_file(
        self,
        delete_on_exit: bool = True,
        calculate_md5_sum: bool = False,
    ) -> None:
        """
        For each instance of ReferenceBuilder in REF_BUILDERS write record to temp file
        """
        # Write temp file path
        with NamedTemporaryFile(
            prefix=f"{self.assembly}_{self.species}",
            suffix=".fasta",
            delete=delete_on_exit,
            mode=("a+t"),
        ) as writer:

            for builder in self.REF_BUILDERS:
                bases = builder.bases
                assembly = builder.assembly
                species = builder.species
                name = builder.name
                header = f">{name}[{assembly}][{species}]\n"
                bases_format = "\n".join(textwrap.wrap(bases, self.line_length))
                try:
                    writer.write(header)
                    writer.write(f"{bases_format}\n\n")
                except OSError as error:
                    raise Exception(f"Could not write to {writer}") from error

        # if calculate_md5_sum:
        # pylint: disable=W0612
        # with open(path.name, "rb") as path_to_read:
        # contents = path_to_read.read()
        # md5 = hashlib.md5(contents).hexdigest()

        # Use md5 to write dict
        # Write .fai

    def to_file(
        self,
        path: Path,
        delete_on_exit: bool = True,
        calculate_md5_sum: bool = False,
    ) -> None:
        """
        Same as to_temp_file() but user provides path
        """
        with path.open("a+") as writer:
            for record in range(len(self.REF_BUILDERS)):
                bases = self.REF_BUILDERS[record].bases
                assembly = self.REF_BUILDERS[record].assembly
                species = self.REF_BUILDERS[record].species
                name = self.REF_BUILDERS[record].name
                header = f">{name}[{assembly}][{species}]\n"
                bases_format = "\n".join(textwrap.wrap(bases, self.line_length))
                try:
                    writer.write(header)
                    writer.write(f"{bases_format}\n\n")
                except OSError as error:
                    print(f"{error}\nCound not write to {writer}")

        # if calculate_md5_sum:
        # with open(path, "rb") as path_to_read:
        # contents = path_to_read.read()
        # md5 = hashlib.md5(contents).hexdigest()

        # Use md5 to write dict
        # Write .fai

        if delete_on_exit:
            os.remove(path)


# pylint: disable=R0903
class ReferenceBuilder:
    """
    Creates individiaul records
    """

    def __init__(
        self,
        name: str,
        assembly: str,
        species: str,
        bases: Optional[str] = str(),
    ):
        self.name = name
        self.assembly = assembly
        self.species = species
        self.bases = bases

    def add(self, bases: str, times: int) -> "ReferenceBuilder":
        """
        "AAA"*3 = AAAAAAAAA
        """
        # add check that bases is not supplied via "AAA "*100
        self.bases += str(bases * times)
        return self


# Scratch
# builder_ex = ReferenceSetBuilder()
# builder_ex.add("chr10").add("NNNNNNNNNN", 1)
# builder_ex.add("chr10").add("AAAAAAAAAA", 2)
# builder_ex.add("chr3").add("GGGGGGGGGG", 10)
# builder_ex.to_file(path="some.fasta", calculate_md5_sum=True, delete_on_exit=True)
# builder_ex.to_temp_file(calculate_md5_sum=True)


# builder_ex = ReferenceSetBuilder()
# b = builder_ex.add("chr10")
# b.add("NNNNNNNNNN", 1)
# b.add("ACGT", 1)
# c = builder_ex.add("chrY").add("NNNNN", 10)
# builder_ex.to_temp_file(calculate_md5_sum=True, delete_on_exit=False)
