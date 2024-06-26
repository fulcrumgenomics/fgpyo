"""
# Classes for generating VCF and records for testing
"""

from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from pysam import VariantHeader
from pysam import VariantRecord

from fgpyo.sam.builder import SamBuilder
from fgpyo.vcf import writer as PysamWriter


class VcfFieldType(Enum):
    """Codes for VCF field types"""

    INTEGER = "Integer"
    FLOAT = "Float"
    FLAG = "Flag"
    CHARACTER = "Character"
    STRING = "String"


class VcfFieldNumber(Enum):
    """Special codes for VCF field numbers"""

    NUM_ALT_ALLELES = "A"
    NUM_ALLELES = "R"
    NUM_GENOTYPES = "G"
    UNKNOWN = "."


MissingRep = Union[None, Tuple[None, ...]]


class VariantBuilder:
    """
    Builder for constructing one or more variant records (pysam.VariantRecord) for a VCF. The VCF
    can be sites-only, single-sample, or multi-sample.

    Provides the ability to manufacture variants from minimal arguments, while generating
    any remaining attributes to ensure a valid variant.

    A builder is constructed with a handful of defaults including the sample name and sequence
    dictionary. If the VCF will not be sites-only, the list of sample IDS ("sample_ids") must be
    provided to the VariantBuilder constructor.

    Variants are then added using the [`add()`][fgpyo.vcf.builder.VariantBuilder.add]
    method.
    Once accumulated the variants can be accessed in the order in which they were created through
    the [`to_unsorted_list()`][fgpyo.vcf.builder.VariantBuilder.to_unsorted_list]
    function, or in a list sorted by coordinate order via
    [`to_sorted_list()`][fgpyo.vcf.builder.VariantBuilder.to_sorted_list]. Lastly, the
    records can be written to a temporary file using
    [`to_path()`][fgpyo.vcf.builder.VariantBuilder.to_path].

    Attributes:
        sample_ids: the sample name(s)
        sd: sequence dictionary, implemented as python dict from contig name to dictionary with
            contig properties. At a minimum, each contig dict in sd must contain "ID" (the same as
            contig_name) and "length", the contig length. Other values will be added to the VCF
            header line for that contig.
        seq_idx_lookup: dictionary mapping contig name to index of contig in sd
        records: the list of variant records
        header: the pysam header
    """

    sample_ids: List[str]
    sd: Dict[str, Dict[str, Any]]
    seq_idx_lookup: Dict[str, int]
    records: List[VariantRecord]
    header: VariantHeader

    def __init__(
        self,
        sample_ids: Optional[Iterable[str]] = None,
        sd: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Initializes a new VariantBuilder for generating variants and VCF files.

        Args:
            sample_ids: the name of the sample(s)
            sd: optional sequence dictionary
        """
        self.sample_ids: List[str] = list(sample_ids) if sample_ids is not None else []
        self.sd: Dict[str, Dict[str, Any]] = sd if sd is not None else VariantBuilder.default_sd()
        self.seq_idx_lookup: Dict[str, int] = {name: i for i, name in enumerate(self.sd.keys())}
        self.records: List[VariantRecord] = []
        self.header = VariantHeader()
        for line in VariantBuilder._build_header_string(sd=self.sd):
            self.header.add_line(line)
        if sample_ids is not None:
            self.header.add_samples(sample_ids)

    @classmethod
    def default_sd(cls) -> Dict[str, Dict[str, Any]]:
        """Generates the sequence dictionary that is used by default by VariantBuilder.
        Re-uses the dictionary from SamBuilder for consistency.

        Returns:
            A new copy of the sequence dictionary as a map of contig name to dictionary, one per
            contig.
        """
        sd: Dict[str, Dict[str, Any]] = {}
        for sequence in SamBuilder.default_sd():
            contig = sequence["SN"]
            sd[contig] = {"ID": contig, "length": sequence["LN"]}
        return sd

    @classmethod
    def _build_header_string(cls, sd: Optional[Dict[str, Dict[str, Any]]] = None) -> Iterator[str]:
        """Builds the VCF header with the given sample name(s) and sequence dictionary.

        Args:
            sd: the sequence dictionary mapping the contig name to the key-value pairs for the
                given contig.  Must include "ID" and "length" for each contig.  If no sequence
                dictionary is given, will use the default dictionary.
        """
        if sd is None:
            sd = VariantBuilder.default_sd()
        # add mandatory VCF format
        yield "##fileformat=VCFv4.2"
        # add GT
        yield '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">'
        # add additional common INFO lines
        yield '##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">'
        yield (
            '##INFO=<ID=AR,Number=A,Type=Float,Description="Allele Ratio - ratio of AD for allele'
            ' vs. AD for modal allele.">'
        )
        yield '##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">'
        # add additional common FORMAT lines
        yield (
            '##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths for the ref and alt'
            ' alleles in the order listed">'
        )
        yield '##FORMAT=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">'
        yield '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Total Depth">'

        for d in sd.values():
            if "ID" not in d or "length" not in d:
                raise ValueError(
                    "Sequence dictionary must include 'ID' and 'length' for each contig."
                )
            contig_id = d["ID"]
            contig_length = d["length"]
            contig_header = f"##contig=<ID={contig_id},length={contig_length}"
            for key, value in d.items():
                if key == "ID" or key == "length":
                    continue
                contig_header += f",{key}={value}"
            contig_header += ">"
            yield contig_header

    @property
    def num_samples(self) -> int:
        return len(self.sample_ids)

    def add(
        self,
        contig: Optional[str] = None,
        pos: int = 1000,
        id: str = ".",
        ref: str = "A",
        alts: Union[None, str, Iterable[str]] = (".",),
        qual: int = 60,
        filter: Union[None, str, Iterable[str]] = None,
        info: Optional[Dict[str, Any]] = None,
        samples: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> VariantRecord:
        """Generates a new variant and adds it to the internal collection.

        Notes:
        * Very little validation is done with respect to INFO and FORMAT keys being defined in the
        header.
        * VCFs are 1-based, but pysam is (mostly) 0-based. We define the function in terms of the
        VCF property "pos", which is 1-based. pysam will also report "pos" as 1-based, so that is
        the property that should be accessed when using the records produced by this function (not
        "start").

        Args:
            contig: the chromosome name. If None, will use the first contig in the sequence
                    dictionary.
            pos: the 1-based position of the variant
            id: the variant id
            ref: the reference allele
            alts: the list of alternate alleles, None if no alternates. If a single string is
                  passed, that will be used as the only alt.
            qual: the variant quality
            filter: the list of filters, None if no filters (ex. PASS). If a single string is
                    passed, that will be used as the only filter.
            info: the dictionary of INFO key-value pairs
            samples: the dictionary from sample name to FORMAT key-value pairs.
                     if a sample property is supplied for any sample but omitted in some, it will
                     be set to missing (".") for samples that don't have that property explicitly
                     assigned. If a sample in the VCF is omitted, all its properties will be set to
                     missing.
        """
        if contig is None:
            contig = next(iter(self.sd.keys()))

        if contig not in self.sd:
            raise ValueError(f"Chromosome `{contig}` not in the sequence dictionary.")
        # because there are a lot of slightly different objects related to samples or called
        # "samples" in this function, we alias samples to sample_formats
        # we still want to keep the API labeled "samples" because that keeps the naming scheme the
        # same as the pysam API
        sample_formats = samples
        if sample_formats is not None:
            unknown_samples = set(sample_formats.keys()).difference(self.sample_ids)
            if len(unknown_samples) > 0:
                raise ValueError("Unknown sample(s) given: " + ", ".join(unknown_samples))

        if isinstance(alts, str):
            alts = (alts,)
        alleles = (ref,) if alts is None else (ref, *alts)
        if isinstance(filter, str):
            filter = (filter,)

        # pysam expects a list of format dicts provided in the same order as the samples in the
        # header (self.sample_ids). (This is despite the fact that it will internally represent the
        # values as a map from sample ID to format values, as we do in this function.)
        # Convert to that form and rename to record_samples; to a) disambiguate from the input
        # values, and b) prevent mypy from complaining about the type changing from dict to list.
        if self.num_samples == 0:
            # this is a sites-only VCF
            record_samples = None
        elif sample_formats is None or len(sample_formats) == 0:
            # not a sites-only VCF, but no FORMAT values were passed. set FORMAT to missing (with
            # no fields)
            record_samples = None
        else:
            # convert to list form that pysam expects, in order pysam expects
            # note: the copy {**format_dict} below is present because pysam actually alters the
            # input values, which would be an unintended side-effect (in fact without this, tests
            # fail because the expected input values are changed)
            record_samples = [
                {**sample_formats.get(sample_id, {})} for sample_id in self.sample_ids
            ]

        # pysam is zero based, half-open [start, stop)
        start = pos - 1  # pysam "start" is zero-based
        stop = start + len(ref)
        variant = self.header.new_record(
            contig=contig,
            start=start,
            stop=stop,
            id=id,
            alleles=alleles,
            qual=qual,
            filter=filter,
            info=info,
            samples=record_samples,
        )

        self.records.append(variant)
        return variant

    def to_path(self, path: Optional[Path] = None) -> Path:
        """Returns a path to a VCF for variants added to this builder.
        Args:
            path: optional path to the VCF
        """
        # update the path
        path = self._to_vcf_path(path)

        # Create a writer and write to it
        with PysamWriter(path, header=self.header) as writer:
            for variant in self.to_sorted_list():
                writer.write(variant)

        return path

    @staticmethod
    def _to_vcf_path(path: Optional[Path]) -> Path:
        """Gets the path to a VCF file.  If path is a directory, a temporary VCF will be created in
        that directory. If path is `None`, then a temporary VCF will be created.  Otherwise, the
        given path is simply returned.

        Args:
            path: optionally the path to the VCF, or a directory to create a temporary VCF.
        """
        if path is None:
            with NamedTemporaryFile(suffix=".vcf", delete=False) as fp:
                path = Path(fp.name)
            assert path.is_file()
        return path

    def to_unsorted_list(self) -> List[VariantRecord]:
        """Returns the accumulated records in the order they were created."""
        return list(self.records)

    def to_sorted_list(self) -> List[VariantRecord]:
        """Returns the accumulated records in coordinate order."""
        return sorted(self.records, key=self._sort_key)

    def _sort_key(self, variant: VariantRecord) -> Tuple[int, int, int]:
        return self.seq_idx_lookup[variant.contig], variant.start, variant.stop

    def add_header_line(self, line: str) -> None:
        """Adds a header line to the header"""
        self.header.add_line(line)

    def add_info_header(
        self,
        name: str,
        field_type: VcfFieldType,
        number: Union[int, VcfFieldNumber] = 1,
        description: Optional[str] = None,
        source: Optional[str] = None,
        version: Optional[str] = None,
    ) -> None:
        """Add an INFO header field to the VCF header.

        Args:
            name: the name of the field
            field_type: the field_type of the field
            number: the number of the field
            description: the description of the field
            source: the source of the field
            version: the version of the field
        """
        if field_type == VcfFieldType.FLAG:
            number = 0  # FLAGs always have number = 0
        header_line = f"##INFO=<ID={name},Number={number},Type={field_type.value}"
        if description is not None:
            header_line += f",Description={description}"
        if source is not None:
            header_line += f",Source={source}"
        if version is not None:
            header_line += f",Version={version}"
        header_line += ">"
        self.add_header_line(header_line)

    def add_format_header(
        self,
        name: str,
        field_type: VcfFieldType,
        number: Union[int, VcfFieldNumber] = VcfFieldNumber.NUM_GENOTYPES,
        description: Optional[str] = None,
    ) -> None:
        """
        Add a FORMAT header field to the VCF header.

        Args:
            name: the name of the field
            field_type: the field_type of the field
            number: the number of the field
            description: the description of the field
        """
        header_line = f"##FORMAT=<ID={name},Number={number},Type={field_type.value}"
        if description is not None:
            header_line += f",Description={description}"
        header_line += ">"
        self.add_header_line(header_line)

    def add_filter_header(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> None:
        """
        Add a FILTER header field to the VCF header.

        Args:
            name: the name of the field
            description: the description of the field
        """
        header_line = f"##FILTER=<ID={name}"
        if description is not None:
            header_line += f",Description={description}"
        header_line += ">"
        self.add_header_line(header_line)
