"""
Classes for generating Fasta files and records for testing
----------------------------------------------------------------
"""
import hashlib
import os
import textwrap

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

    # Sample name tuple
    SAMPLE_NAMES = []

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

        builder = ReferenceBuilder(name=name, assembly=self.assembly, species=self.species)
        self.REF_BUILDERS.append(builder)
        return self.REF_BUILDERS[-1]

    def writer_helper(
        self,
    ):
        """ Place holder for helper funciton """
        return None

    def to_temp_file(
        self,
        delete_on_exit: Optional[bool] = None,
        calculate_md5_sum: Optional[bool] = None,
    ):
        """
        For each instance of ReferenceBuilder in REF_BUILDERS write record to temp file
        """
        # Set defaults
        delete_on_exit: bool = delete_on_exit if delete_on_exit is not None else True
        calculate_md5_sum: bool = calculate_md5_sum if calculate_md5_sum is not None else False

        # Write temp file path
        path = NamedTemporaryFile(
            prefix=f"{self.assembly}_{self.species}",
            suffix=".fasta",
            delete=delete_on_exit,
            mode=("a+t"),
        )

        # TODO clean and conver to map if possible
        for record in enumerate(self.REF_BUILDERS):
            record = record[0]
            seq = self.REF_BUILDERS[record].sequences
            assembly = self.REF_BUILDERS[record].assembly
            species = self.REF_BUILDERS[record].species
            name = self.REF_BUILDERS[record].name
            header = f">{name}[{assembly}][{species}]\n"
            seq_format = "\n".join(textwrap.wrap(seq, self.line_length))
            try:
                path.write(header)
                path.write(f"{seq_format}\n\n")
            except OSError as error:
                print(f"{error}\nCound not write to {path}")

        if calculate_md5_sum:
            # pylint: disable=W0612
            with open(path.name, "rb") as path_to_read:
                contents = path_to_read.read()
                md5 = hashlib.md5(contents).hexdigest()

        # Use md5 to write dict
        # Write .fai

        path.close()

    def to_file(
        self,
        path: str,
        delete_on_exit: Optional[bool] = None,
        calculate_md5_sum: Optional[bool] = None,
    ):
        """
        Same as to_temp_file() but user provides path
        """

        # Set defaults
        delete_on_exit: bool = delete_on_exit if delete_on_exit is not None else True
        calculate_md5_sum: bool = calculate_md5_sum if calculate_md5_sum is not None else False

        # Refactor into map with helper function
        with open(path, "a+") as fasta_handle:
            for record in enumerate(self.REF_BUILDERS):
                record = record[0]
                seq = self.REF_BUILDERS[record].sequences
                assembly = self.REF_BUILDERS[record].assembly
                species = self.REF_BUILDERS[record].species
                name = self.REF_BUILDERS[record].name
                header = f">{name}[{assembly}][{species}]\n"
                seq_format = "\n".join(textwrap.wrap(seq, self.line_length))
                fasta_handle.writelines(header)
                fasta_handle.writelines(f"{seq_format}\n\n")

        if calculate_md5_sum:
            # pylint: disable=W0612
            with open(path, "rb") as path_to_read:
                contents = path_to_read.read()
                md5 = hashlib.md5(contents).hexdigest()

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
        # add check that seq is not supplied via "AAA "*100
        self.sequences = seq * times


### Scratch ###
# builder_ex = ReferenceSetBuilder()
# builder_ex.add("chr10").add("NNNNNNNNNN", 1)
# builder_ex.add("chr10").add("AAAAAAAAAA", 2)
# builder_ex.add("chr3").add("GGGGGGGGGG", 10)
# builder_ex.to_file(path="some.fasta", calculate_md5_sum=True, delete_on_exit=True)
# builder_ex.to_temp_file(calculate_md5_sum=True)
