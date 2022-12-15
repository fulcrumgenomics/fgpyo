"""
Classes for generating Fasta files and records for testing
----------------------------------------------------------
"""
# import hashlib
import os
import textwrap
from tempfile import NamedTemporaryFile
from typing import ClassVar
from typing import List
from typing import Optional


class ReferenceSetBuilder:
    """
    Builder for constructing one or more fasta records.
    """

    # The default asssembly
    DEFAULT_ASSEMBLY: ClassVar[str] = "testassembly"

    # The default species
    DEFAULT_SPECIES: ClassVar[str] = "testspecies"

    # Way to store instance of ReferenceBuilder
    # TODO make something better than a list... probably
    REF_BUILDERS: List["ReferenceBuilder"] = []

    def __init__(
        self,
        assembly: Optional[str] = None,
        species: Optional[str] = None,
        line_length: int = 80,
    ):
        self.assembly: str = assembly if assembly is not None else self.DEFAULT_ASSEMBLY
        self.species: str = species if species is not None else self.DEFAULT_SPECIES
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
        path = NamedTemporaryFile(
            prefix=f"{self.assembly}_{self.species}",
            suffix=".fasta",
            delete=delete_on_exit,
            mode=("a+t"),
        )

        for builder in self.REF_BUILDERS:
            sequences = builder.sequences
            assembly = builder.assembly
            species = builder.species
            name = builder.name
            header = f">{name}[{assembly}][{species}]\n"
            seq_format = "\n".join(textwrap.wrap(sequences, self.line_length))
            try:
                path.write(header)
                path.write(f"{seq_format}\n\n")
            except OSError as error:
                raise Exception(f"Could not write to {path}") from error

        # if calculate_md5_sum:
        # pylint: disable=W0612
        # with open(path.name, "rb") as path_to_read:
        # contents = path_to_read.read()
        # md5 = hashlib.md5(contents).hexdigest()

        # Use md5 to write dict
        # Write .fai

        path.close()

    def to_file(
        self,
        path: str,
        delete_on_exit: Optional[bool] = True,
        calculate_md5_sum: Optional[bool] = False,
    ) -> None:
        """
        Same as to_temp_file() but user provides path
        """
        with open(path, "a+") as fasta_handle:
            for record in range(len(self.REF_BUILDERS)):
                seq = self.REF_BUILDERS[record].sequences
                assembly = self.REF_BUILDERS[record].assembly
                species = self.REF_BUILDERS[record].species
                name = self.REF_BUILDERS[record].name
                header = f">{name}[{assembly}][{species}]\n"
                seq_format = "\n".join(textwrap.wrap(seq, self.line_length))
                try:
                    fasta_handle.write(header)
                    fasta_handle.write(f"{seq_format}\n\n")
                except OSError as error:
                    print(f"{error}\nCound not write to {path}")

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
        sequences: Optional[str] = str(),
    ):
        self.name = name
        self.assembly = assembly
        self.species = species
        self.sequences = sequences

    def add(self, seq: str, times: int) -> "ReferenceBuilder":
        """
        "AAA"*3 = AAAAAAAAA
        """
        # add check that seq is not supplied via "AAA "*100
        self.sequences += str(seq * times)
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
# builder_ex.to_file(path="some.fasta", calculate_md5_sum=True, delete_on_exit=False)
