from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Union

import pysam
import pytest

from fgpyo.fasta.sequence_dictionary import AlternateLocus
from fgpyo.fasta.sequence_dictionary import Keys
from fgpyo.fasta.sequence_dictionary import SequenceDictionary
from fgpyo.fasta.sequence_dictionary import SequenceMetadata
from fgpyo.fasta.sequence_dictionary import Topology
from fgpyo.sam import builder
from fgpyo.sam import reader


def test_alternate_locus_raises_start_gt_end() -> None:
    with pytest.raises(ValueError, match="start > end"):
        AlternateLocus(name="chr1", start=10, end=9)


def test_alternate_locus_raises_start_lt_one() -> None:
    with pytest.raises(ValueError, match="start < 1"):
        AlternateLocus(name="chr1", start=0, end=9)


def test_alternate_locus_ok() -> None:
    assert len(AlternateLocus(name="chr1", start=10, end=10)) == 1
    assert len(AlternateLocus(name="chr1", start=1, end=10)) == 10


@pytest.mark.parametrize(
    "value, expected",
    [
        ("chr1:1-1", AlternateLocus(name="chr1", start=1, end=1)),
        ("foo:100-200", AlternateLocus(name="foo", start=100, end=200)),
    ],
)
def test_alternate_locus_parse(value: str, expected: AlternateLocus) -> None:
    assert AlternateLocus.parse(value) == expected


def test_sequence_metadata_raises_negative_length() -> None:
    with pytest.raises(ValueError, match="Length must be >= 0"):
        SequenceMetadata(name="chr1", length=-1, index=0)


def test_sequence_metadata_raises_illegal_name() -> None:
    with pytest.raises(ValueError, match="Illegal name"):
        SequenceMetadata(name="chromosome one", length=1, index=100)


def test_sequence_metadata_raises_sequence_name_in_attributes() -> None:
    match_key = f"'{Keys.SEQUENCE_NAME}' should not given in the list of attributes"
    with pytest.raises(ValueError, match=match_key):
        SequenceMetadata(name="1", length=1, index=1, attributes={Keys.SEQUENCE_NAME: "SN"})


def test_sequence_metadata_raises_sequence_length_in_attributes() -> None:
    match_key = f"'{Keys.SEQUENCE_LENGTH}' should not given in the list of attributes"
    with pytest.raises(ValueError, match=match_key):
        SequenceMetadata(name="1", length=1, index=1, attributes={Keys.SEQUENCE_LENGTH: "12"})


def test_sequence_metadata_aliases() -> None:
    assert SequenceMetadata(name="1", length=1, index=0).aliases == []
    assert SequenceMetadata(
        name="1", length=1, index=0, attributes={Keys.ALIASES: "2,3,45"}
    ).aliases == ["2", "3", "45"]


def test_sequence_metadata_all_names() -> None:
    assert SequenceMetadata(name="1", length=1, index=0).all_names == ["1"]
    assert SequenceMetadata(
        name="1", length=1, index=0, attributes={Keys.ALIASES: "2,3,45"}
    ).all_names == ["1", "2", "3", "45"]


def test_sequence_metadata_alternate() -> None:
    meta = SequenceMetadata(name="1", length=1, index=0)
    assert meta.alternate is None
    assert not meta.is_alternate

    meta = SequenceMetadata(name="1", length=1, index=0, attributes={Keys.ALTERNATE_LOCUS: "*"})
    assert meta.alternate is None
    assert not meta.is_alternate

    meta = SequenceMetadata(name="1", length=1, index=0, attributes={Keys.ALTERNATE_LOCUS: "=:2-3"})
    assert meta.alternate == AlternateLocus(name="1", start=2, end=3)
    assert meta.is_alternate

    meta = SequenceMetadata(name="1", length=1, index=0, attributes={Keys.ALTERNATE_LOCUS: "4:2-3"})
    assert meta.alternate == AlternateLocus(name="4", start=2, end=3)
    assert meta.is_alternate


def test_sequence_metadata_keys() -> None:
    meta = SequenceMetadata(name="1", length=1, index=0)
    for key in Keys.attributes():
        assert meta.get(key) is None, f"key: {key} meta: {meta}"
    assert meta[Keys.SEQUENCE_NAME] == "1"
    assert meta[Keys.SEQUENCE_LENGTH] == "1"
    assert meta.length == 1
    assert len(meta) == 1

    valid_attributes = Keys.attributes()
    attributes = {key: f"value-{key}" for key in valid_attributes}
    attributes[Keys.TOPOLOGY] = Topology.LINEAR  # override as topology has a specific set of values
    meta = SequenceMetadata(name="1", length=1, index=0, attributes=attributes)
    for key in Keys:
        if key in valid_attributes:
            assert meta.get(key) is not None, f"key: {key} meta: {meta}"
            assert meta[key] == attributes[key]
    assert meta[Keys.SEQUENCE_NAME] == "1"
    assert meta[Keys.SEQUENCE_LENGTH] == "1"
    assert meta.length == 1
    assert len(meta) == 1

    assert meta.md5 == attributes[Keys.MD5]
    assert meta.assembly == attributes[Keys.ASSEMBLY]
    assert meta.uri == attributes[Keys.URI]
    assert meta.species == attributes[Keys.SPECIES]
    assert meta.description == attributes[Keys.DESCRIPTION]
    assert meta.topology == Topology[attributes[Keys.TOPOLOGY]]


@pytest.mark.parametrize(
    "this, that, expected",
    [
        # all but the names are different
        (
            SequenceMetadata(name="chr1", length=10, index=0),
            SequenceMetadata(name="chr2", length=10, index=0),
            False,
        ),
        # all but the lengths are different
        (
            SequenceMetadata(name="chr1", length=10, index=0),
            SequenceMetadata(name="chr1", length=9, index=0),
            False,
        ),
        # all but the md5 are different
        (
            SequenceMetadata(name="chr1", length=10, index=0, attributes={Keys.MD5: "foo"}),
            SequenceMetadata(name="chr1", length=10, index=0, attributes={Keys.MD5: "bar"}),
            False,
        ),
        # no common name, even with aliases
        (
            SequenceMetadata(name="chr1", length=10, index=0, attributes={Keys.ALIASES: "foo,bar"}),
            SequenceMetadata(name="chr2", length=10, index=0),
            False,
        ),
        # exactly the same
        (
            SequenceMetadata(name="chr1", length=10, index=0),
            SequenceMetadata(name="chr1", length=10, index=0),
            True,
        ),
        # expected True even though index is different
        (
            SequenceMetadata(name="chr1", length=10, index=0),
            SequenceMetadata(name="chr1", length=10, index=1),
            True,
        ),
        # expected True even though (non-MD5) attributes are different
        (
            SequenceMetadata(name="chr1", length=10, index=0, attributes={Keys.ASSEMBLY: "foo"}),
            SequenceMetadata(name="chr1", length=10, index=0, attributes={Keys.ASSEMBLY: "bar"}),
            True,
        ),
        # expected True when there the same, but the name is in the alias of the other
        (
            SequenceMetadata(
                name="chr1", length=10, index=0, attributes={Keys.ALIASES: "foo,chr2"}
            ),
            SequenceMetadata(
                name="chr2", length=10, index=0, attributes={Keys.ALIASES: "foo,chr1"}
            ),
            True,
        ),
    ],
)
def test_sequence_metadata_same_as(
    this: SequenceMetadata, that: SequenceMetadata, expected: bool
) -> None:
    assert this.same_as(other=that) == expected
    assert that.same_as(other=this) == expected
    assert that.same_as(other=that)
    assert this.same_as(other=this)


def test_sequence_metadata_to_and_from_sam() -> None:
    valid_attributes = Keys.attributes()
    attributes = {key: f"value-{key}" for key in valid_attributes}
    attributes[Keys.TOPOLOGY] = Topology.LINEAR  # override as topology has a specific set of values
    attributes[Keys.ALTERNATE_LOCUS] = "chr2:3-4"
    meta = SequenceMetadata(name="1", length=1, index=0, attributes=attributes)

    sam_dict: Dict[Union[Keys, str], Any] = {
        Keys.SEQUENCE_NAME: meta.name,
        Keys.SEQUENCE_LENGTH: meta.length,
        Keys.ALIASES: ",".join(meta.aliases),
        Keys.ALTERNATE_LOCUS: f"{meta.alternate}",
        Keys.ASSEMBLY: f"{meta.assembly}",
        Keys.DESCRIPTION: f"{meta.description}",
        Keys.MD5: meta.md5,
        Keys.SPECIES: meta.species,
        Keys.TOPOLOGY: f"{meta.topology}",
        Keys.URI: meta.uri,
    }

    assert meta.to_sam() == sam_dict
    assert SequenceMetadata.from_sam(meta=sam_dict, index=0) == meta


def test_sequence_dictionary_mutable_mapping() -> None:
    meta = SequenceMetadata(
        name="1",
        length=123,
        index=0,
        attributes={Keys.MD5: "md5", Keys.ALIASES: "2", Keys.ASSEMBLY: "as"},
    )
    # __getitem__
    assert meta[Keys.MD5] == "md5"
    # __setitem__
    meta[Keys.MD5] = "foo"
    assert meta[Keys.MD5] == "foo"
    for key in [Keys.SEQUENCE_NAME, Keys.SEQUENCE_LENGTH]:
        with pytest.raises(KeyError, match="Cannot set"):
            meta[key] = "foo"
    # __delitem__
    del meta[Keys.MD5]
    assert Keys.MD5 not in meta
    assert meta.get(Keys.MD5) is None
    for key in [Keys.SEQUENCE_NAME, Keys.SEQUENCE_LENGTH]:
        with pytest.raises(KeyError, match="Cannot delete"):
            del meta[key]
    # __iter__
    assert list(meta) == [Keys.SEQUENCE_NAME, Keys.SEQUENCE_LENGTH, Keys.ALIASES, Keys.ASSEMBLY]
    # __len__
    assert len(meta) == 123
    # other methods
    assert list(meta.values()) == ["1", "123", "2", "as"]
    assert list(meta.items()) == [
        (Keys.SEQUENCE_NAME, "1"),
        (Keys.SEQUENCE_LENGTH, "123"),
        (Keys.ALIASES, "2"),
        (Keys.ASSEMBLY, "as"),
    ]


@pytest.mark.parametrize(
    "infos",
    [
        [
            SequenceMetadata(name="chr1", length=0, index=0),
            SequenceMetadata(name="chr1", length=0, index=2),
        ],
        [
            SequenceMetadata(name="chr1", length=0, index=1),
            SequenceMetadata(name="chr1", length=0, index=0),
        ],
        [
            SequenceMetadata(name="chr1", length=0, index=0),
            SequenceMetadata(name="chr1", length=0, index=0),
        ],
        [
            SequenceMetadata(name="chr1", length=0, index=1),
            SequenceMetadata(name="chr1", length=0, index=2),
        ],
    ],
)
def test_sequence_dictionary_index_out_of_order(infos: List[SequenceMetadata]) -> None:
    with pytest.raises(ValueError, match="Infos must be given with index set correctly."):
        SequenceDictionary(infos=infos)


@pytest.mark.parametrize(
    "infos",
    [
        [
            SequenceMetadata(name="chr1", length=0, index=0),
            SequenceMetadata(name="chr1", length=0, index=1),
        ],
        [
            SequenceMetadata(name="chr1", length=0, index=0),
            SequenceMetadata(name="chr2", length=0, index=1, attributes={Keys.ALIASES: "chr1"}),
        ],
        [
            SequenceMetadata(name="chr1", length=0, index=0, attributes={Keys.ALIASES: "chr2"}),
            SequenceMetadata(name="chr2", length=0, index=1),
        ],
    ],
)
def test_sequence_dictionary_duplicate_names(infos: List[SequenceMetadata]) -> None:
    with pytest.raises(ValueError, match="Found duplicate sequence name"):
        SequenceDictionary(infos=infos)


def test_sequence_dictionary_same_as() -> None:
    this = SequenceDictionary(
        infos=[
            SequenceMetadata(name="chr1", length=0, index=0),
            SequenceMetadata(name="chr2", length=0, index=1),
        ]
    )
    that = SequenceDictionary(
        infos=[
            SequenceMetadata(name="chr2", length=0, index=0),
            SequenceMetadata(name="chr3", length=0, index=1),
        ]
    )
    assert this.same_as(this)
    assert that.same_as(that)
    assert not this.same_as(that)


def test_sequence_dictionary_to_and_from_sam() -> None:
    sd = SequenceDictionary(
        infos=[
            SequenceMetadata(name="chr1", length=10, index=0),
            SequenceMetadata(name="chr2", length=20, index=1, attributes={Keys.ALIASES: "chr3"}),
        ]
    )
    mapping: List[Dict[str, Any]] = [
        {Keys.SEQUENCE_NAME: "chr1", Keys.SEQUENCE_LENGTH: 10},
        {Keys.SEQUENCE_NAME: "chr2", Keys.SEQUENCE_LENGTH: 20, Keys.ALIASES: "chr3"},
    ]
    header = pysam.AlignmentHeader.from_dict(
        header_dict={"HD": {"VN": "1.5"}, "SQ": mapping, "RG": [{"ID": "foo"}]}
    )
    samfile: Path = builder.SamBuilder(sd=mapping).to_path()
    with reader(samfile) as alignment_fh:  # pysam.AlignmentFile
        assert SequenceDictionary.from_sam(alignment_fh) == sd
    assert SequenceDictionary.from_sam(samfile) == sd
    assert SequenceDictionary.from_sam(mapping) == sd
    assert SequenceDictionary.from_sam(header) == sd
    assert sd.to_sam_header(extra_header={"RG": [{"ID": "foo"}]})
    with pytest.raises(ValueError):
        SequenceDictionary.from_sam([{}])


def test_sequence_dictionary_mapping() -> None:
    sd = SequenceDictionary(
        infos=[
            SequenceMetadata(name="chr1", length=10, index=0),
            SequenceMetadata(name="chr2", length=20, index=1, attributes={Keys.ALIASES: "chr3"}),
        ]
    )
    # __getitem__
    assert sd["chr1"] == sd.infos[0]
    assert sd["chr2"] == sd.infos[1]
    assert sd["chr3"] == sd.infos[1]  # alias
    assert sd[0] == sd.infos[0]
    assert sd[1] == sd.infos[1]
    with pytest.raises(IndexError):
        sd[2]
    with pytest.raises(KeyError):
        sd["chr4"]
    # __iter__
    assert list(iter(sd)) == ["chr1", "chr2", "chr3"]
    # __len__
    assert len(sd) == 2
    # other methods
    assert list(sd.values()) == sd.infos + [sd.infos[1]]
    assert list(sd.items()) == [
        ("chr1", sd.infos[0]),
        ("chr2", sd.infos[1]),
        ("chr3", sd.infos[1]),
    ]
