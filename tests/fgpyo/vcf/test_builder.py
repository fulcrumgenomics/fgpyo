import gzip
import random
from pathlib import Path
from types import MappingProxyType
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Tuple

import pysam
import pytest

from fgpyo.vcf import reader as vcf_reader
from fgpyo.vcf.builder import VariantBuilder
from fgpyo.vcf.builder import VcfFieldType


@pytest.fixture(scope="function")
def temp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("test_vcf")


@pytest.fixture(scope="function")
def random_generator(seed: int = 42) -> random.Random:
    return random.Random(seed)


@pytest.fixture(scope="function")
def sequence_dict() -> Dict[str, Dict[str, Any]]:
    return VariantBuilder.default_sd()


def _get_random_contig(
    random_generator: random.Random, sequence_dict: Dict[str, Dict[str, Any]]
) -> Tuple[str, int]:
    """Randomly select a contig from the sequence dictionary and return its name and length."""
    contig = random_generator.choice(list(sequence_dict.values()))
    return contig["ID"], contig["length"]


_ALL_FILTERS = frozenset({"MAYBE", "FAIL", "SOMETHING"})
_INFO_FIELD_TYPES = MappingProxyType(
    {
        "TEST_INT": VcfFieldType.INTEGER,
        "TEST_STR": VcfFieldType.STRING,
        "TEST_FLOAT": VcfFieldType.FLOAT,
    }
)


def _get_random_variant_inputs(
    random_generator: random.Random,
    sequence_dict: Dict[str, Dict[str, Any]],
) -> Mapping[str, Any]:
    """
    Randomly generate inputs that should produce a valid Variant. Don't include format fields.
    """
    contig, contig_len = _get_random_contig(random_generator, sequence_dict)
    variant_reference_len = random_generator.choice([0, 1, 5, 100])
    variant_read_len = random_generator.choice(
        [1, 5, 100] if variant_reference_len == 0 else [0, 1, 5, 100]
    )
    num_filters = random_generator.randint(0, 3)
    filter = tuple(random_generator.sample(list(_ALL_FILTERS), k=num_filters))
    start = random_generator.randint(1, contig_len - variant_reference_len)
    # stop is not directly passed by current API, but this is what its value would be:
    # stop = start + variant_reference_len
    ref = "".join(random_generator.choices("ATCG", k=variant_reference_len))
    alt = ref
    while alt == ref:
        alt = "".join(random_generator.choices("ATCG", k=variant_read_len))
    if variant_reference_len == 0 or variant_read_len == 0:
        # represent ref/alt for insertions/deletions as starting with the last unaltered base.
        random_start = random_generator.choices("ATCG")[0]
        ref = random_start + ref
        alt = random_start + alt

    info = {
        key: (
            random_generator.randint(0, 100)
            if value_type == VcfFieldType.INTEGER
            else (
                random_generator.uniform(0, 1)
                if value_type == VcfFieldType.FLOAT
                else random_generator.choice(["Up", "Down"])
            )
        )
        for key, value_type in _INFO_FIELD_TYPES.items()
    }

    return MappingProxyType(
        {
            "contig": contig,
            "pos": start,
            "ref": ref,
            "alts": (alt,),
            "filter": filter,
            "info": info,
        }
    )


@pytest.fixture(scope="function")
def zero_sample_record_inputs(
    random_generator: random.Random, sequence_dict: Dict[str, Dict[str, Any]]
) -> Tuple[Mapping[str, Any], ...]:
    """
    Fixture with inputs to create test Variant records for zero-sample VCFs (no genotypes).
    Make them MappingProxyType so that they are immutable.
    """
    return tuple(_get_random_variant_inputs(random_generator, sequence_dict) for _ in range(100))


def _add_headers(variant_builder: VariantBuilder) -> None:
    """Add needed headers to the VariantBuilder."""
    for filter in _ALL_FILTERS:
        variant_builder.add_filter_header(filter)
    for field_name, field_type in _INFO_FIELD_TYPES.items():
        variant_builder.add_info_header(field_name, field_type=field_type)


def _fix_value(value: Any) -> Any:
    """Helper to convert pysam data types to basic python types for testing/comparison."""
    if isinstance(value, pysam.VariantRecord):
        return {
            "contig": value.contig,
            "id": value.id,
            "pos": value.pos,
            "ref": value.ref,
            "qual": value.qual,
            "alts": _fix_value(value.alts),
            "filter": _fix_value(value.filter),
            "info": _fix_value(value.info),
            "samples": _fix_value(value.samples),
        }
    elif isinstance(value, str):
        # this has __iter__, so just get it out of the way early
        return value
    elif isinstance(value, float):
        return round(value, 4)  # only keep a few decimal places, VCF changes type, rounds, etc
    elif isinstance(value, pysam.VariantRecordFilter):
        return tuple(value.keys())
    elif hasattr(value, "items"):
        return {_key: _fix_value(_value) for _key, _value in value.items()}
    elif hasattr(value, "__iter__"):
        return tuple(_fix_value(_value) for _value in value)
    else:
        return value


def _assert_equal(expected_value: Any, actual_value: Any) -> None:
    """Helper to assert that two values are equal, handling pysam data types."""
    __tracebackhide__ = True
    assert _fix_value(expected_value) == _fix_value(actual_value)


def test_minimal_inputs() -> None:
    """Show that all inputs can be None and the builder will succeed."""
    variant_builder = VariantBuilder()
    variant_builder.add()
    variants = variant_builder.to_sorted_list()
    assert len(variants) == 1
    assert isinstance(variants[0], pysam.VariantRecord)
    assert variants[0].contig == "chr1"  # 1st contig in the default sequence dictionary

    # now the same, but with a non-default sequence dictionary
    non_standard_sequence_dict = {"contig1": {"ID": "contig1", "length": 10000}}
    variant_builder = VariantBuilder(sd=non_standard_sequence_dict)
    variant_builder.add()
    variants = variant_builder.to_sorted_list()
    assert len(variants) == 1
    assert isinstance(variants[0], pysam.VariantRecord)
    assert variants[0].contig == "contig1"


def test_sort_order(random_generator: random.Random) -> None:
    """Test if the VariantBuilder sorts the Variant records in the correct order."""
    sorted_inputs: List[Dict[str, Any]] = [
        {"contig": "chr1", "pos": 100},
        {"contig": "chr1", "pos": 500},
        {"contig": "chr2", "pos": 1000},
        {"contig": "chr2", "pos": 10000},
        {"contig": "chr10", "pos": 10},
        {"contig": "chr10", "pos": 20},
        {"contig": "chr11", "pos": 5},
    ]
    scrambled_inputs: List[Dict[str, Any]] = random_generator.sample(
        sorted_inputs, k=len(sorted_inputs)
    )
    assert scrambled_inputs != sorted_inputs  # there should be something to actually sort
    variant_builder = VariantBuilder()
    for record_input in scrambled_inputs:
        variant_builder.add(**record_input)

    for sorted_input, variant_record in zip(sorted_inputs, variant_builder.to_sorted_list()):
        for key, value in sorted_input.items():
            _assert_equal(expected_value=value, actual_value=getattr(variant_record, key))


def test_zero_sample_records_match_inputs(
    zero_sample_record_inputs: Tuple[Mapping[str, Any]],
) -> None:
    """Test if zero-sample VCF (no genotypes) records produced match the requested inputs."""
    variant_builder = VariantBuilder()
    _add_headers(variant_builder)
    for record_input in zero_sample_record_inputs:
        variant_builder.add(**record_input)

    for record_input, variant_record in zip(
        zero_sample_record_inputs, variant_builder.to_unsorted_list()
    ):
        for key, value in record_input.items():
            _assert_equal(expected_value=value, actual_value=getattr(variant_record, key))


def _get_is_compressed(input_file: Path) -> bool:
    """Returns True if the input file is gzip-compressed, False otherwise."""
    with gzip.open(f"{input_file}", "r") as f_in:
        try:
            f_in.read(1)
            return True
        except OSError:
            return False


@pytest.mark.parametrize("compress", (True, False))
def test_zero_sample_vcf_round_trip(
    temp_path: Path,
    zero_sample_record_inputs: Tuple[Mapping[str, Any], ...],
    compress: bool,
) -> None:
    """
    Test if zero-sample VCF (no genotypes) output records match the records read in from the
    resulting VCF.
    """
    vcf = temp_path / ("test.vcf.gz" if compress else "test.vcf")
    variant_builder = VariantBuilder()
    _add_headers(variant_builder)
    for record_input in zero_sample_record_inputs:
        variant_builder.add(**record_input)

    variant_builder.to_path(vcf)

    # this can fail if pysam.VariantFile is not invoked correctly with pathlib.Path objects
    assert _get_is_compressed(vcf) == compress

    with vcf_reader(vcf) as reader:
        for vcf_record, builder_record in zip(reader, variant_builder.to_sorted_list()):
            _assert_equal(expected_value=builder_record, actual_value=vcf_record)


def _add_random_genotypes(
    random_generator: random.Random,
    record_input: Mapping[str, Any],
    sample_ids: Iterable[str],
) -> Mapping[str, Any]:
    """Add random genotypes to the record input."""
    genotypes = {
        sample_id: {
            "GT": random_generator.choice(
                [
                    (None,),
                    (0, 0),
                    (0, 1),
                    (1, 0),
                    (1, 1),
                    (None, 0),
                    (0, None),
                    (1, None),
                ]
            )
        }
        for sample_id in sample_ids
    }
    return MappingProxyType({**record_input, "samples": genotypes})


@pytest.mark.parametrize("num_samples", (1,))
@pytest.mark.parametrize("add_genotypes_to_records", (True, False))
def test_variant_sample_records_match_inputs(
    random_generator: random.Random,
    zero_sample_record_inputs: Tuple[Mapping[str, Any]],
    num_samples: int,
    add_genotypes_to_records: bool,
) -> None:
    """
    Test if records with samples / genotypes match the requested inputs.
    If add_genotypes is True, then add random genotypes to the record input, otherwise test that
    the VariantBuilder will work even if genotypes are not supplied.
    """
    sample_ids = [f"sample{i}" for i in range(num_samples)]
    variant_builder = VariantBuilder(sample_ids=sample_ids)
    _add_headers(variant_builder)
    variant_sample_records = (
        tuple(
            _add_random_genotypes(
                random_generator=random_generator, record_input=record_input, sample_ids=sample_ids
            )
            for record_input in zero_sample_record_inputs
        )
        if add_genotypes_to_records
        else zero_sample_record_inputs
    )
    for record_input in variant_sample_records:
        variant_builder.add(**record_input)

    for record_input, variant_record in zip(
        variant_sample_records, variant_builder.to_unsorted_list()
    ):
        for key, input_value in record_input.items():
            _assert_equal(expected_value=input_value, actual_value=getattr(variant_record, key))


@pytest.mark.parametrize("num_samples", (1, 5))
@pytest.mark.parametrize("compress", (True, False))
@pytest.mark.parametrize("add_genotypes_to_records", (True, False))
def test_variant_sample_vcf_round_trip(
    temp_path: Path,
    random_generator: random.Random,
    zero_sample_record_inputs: Tuple[Mapping[str, Any]],
    num_samples: int,
    compress: bool,
    add_genotypes_to_records: bool,
) -> None:
    """
    Test if 1 or multi-sample VCF output records match the records read in from the resulting VCF.
    If add_genotypes is True, then add random genotypes to the record input, otherwise test that
    the VariantBuilder will work even if genotypes are not supplied.
    """
    sample_ids = [f"sample{i}" for i in range(num_samples)]
    vcf = temp_path / ("test.vcf.gz" if compress else "test.vcf")
    variant_builder = VariantBuilder(sample_ids=sample_ids)
    _add_headers(variant_builder)
    variant_sample_records = (
        tuple(
            _add_random_genotypes(
                random_generator=random_generator, record_input=record_input, sample_ids=sample_ids
            )
            for record_input in zero_sample_record_inputs
        )
        if add_genotypes_to_records
        else zero_sample_record_inputs
    )
    for record_input in variant_sample_records:
        variant_builder.add(**record_input)
    variant_builder.to_path(vcf)

    # this can fail if pysam.VariantFile is not invoked correctly with pathlib.Path objects
    assert _get_is_compressed(vcf) == compress

    with vcf_reader(vcf) as reader:
        for vcf_record, builder_record in zip(reader, variant_builder.to_sorted_list()):
            _assert_equal(expected_value=builder_record, actual_value=vcf_record)
