import functools
from typing import Iterable

from pysam import VariantHeader
from pysam import VariantRecord


class VariantOrdering:
    """Utility class for ordering VCF variants.

    This class provides methods to sort VCF variants by their genomic coordinates.

    Attributes:
        header (VariantHeader): The header of the VCF file.
    """

    def __init__(self, header: VariantHeader) -> None:
        """Initialize VariantOrdering with a VCF header.

        Args:
            header (VariantHeader): The header of a VCF file.
        """
        self.header = header

    def validate_contig(self, rec: VariantRecord) -> None:
        """Check if the contig of a VariantRecord is known in the VCF header.

        Args:
            rec: The variant record to check.

        Raises:
            ValueError: If the contig is not known in the VCF header.
        """
        if rec.contig not in self.header.contigs:
            raise ValueError(f"Contig '{rec.contig}' not found in VCF header.")

    def eq(self, rec1: VariantRecord, rec2: VariantRecord) -> bool:
        """Check if two VariantRecords share the same start coordinate.

        Args:
            rec1: The first variant record.
            rec2: The second variant record.

        Returns:
            bool: True if the variant records share the same start coordinate, False otherwise.
        """
        self.validate_contig(rec1)
        self.validate_contig(rec2)
        return rec1.contig == rec2.contig and rec1.pos == rec2.pos

    def lt(self, rec1: VariantRecord, rec2: VariantRecord) -> bool:
        """Check if the first VariantRecord is less than the second based on genomic coordinates.

        Args:
            rec1: The first variant record.
            rec2: The second variant record.

        Returns:
            bool: True if the first variant record is less than the second, False otherwise.
        """
        self.validate_contig(rec1)
        self.validate_contig(rec2)
        return self.header.contigs.get(rec1.contig).id < self.header.contigs.get(
            rec2.contig
        ).id or (rec1.contig == rec2.contig and rec1.pos < rec2.pos)

    def gt(self, rec1: VariantRecord, rec2: VariantRecord) -> bool:
        """Check if the first VariantRecord is greater than the second based on genomic coordinates.

        Args:
            rec1: The first variant record.
            rec2: The second variant record.

        Returns:
            bool: True if the first variant record is greater than the second, False otherwise.
        """
        self.validate_contig(rec1)
        self.validate_contig(rec2)
        return self.header.contigs.get(rec1.contig).id > self.header.contigs.get(
            rec2.contig
        ).id or (rec1.contig == rec2.contig and rec1.pos > rec2.pos)

    def cmp(self, rec1: VariantRecord, rec2: VariantRecord) -> int:
        """Compare two VariantRecords based on genomic coordinates.

        Args:
            rec1: The first variant record.
            rec2: The second variant record.

        Returns:
            int: -1 if the first variant record is less than the second,
                1 if the first variant record is greater than the second,
                0 if they are equal.
        """
        if self.lt(rec1, rec2):
            return -1
        elif self.gt(rec1, rec2):
            return 1
        else:
            return 0

    def sort_variants(self, records: Iterable[VariantRecord]) -> list[VariantRecord]:
        """Sort variant records using the VariantOrdering comparison.

        Args:
            records: An iterable of VariantRecord objects.

        Returns:
            A list of sorted VariantRecord objects.
        """
        return sorted(records, key=functools.cmp_to_key(self.cmp))
