"""
# Classes for representing sequencing dictionaries.

## Examples of building and using sequence dictionaries

Building a sequence dictionary from a `pysam.AlignmentHeader`:

```python
>>> import pysam
>>> from fgpyo.fasta.sequence_dictionary import SequenceDictionary
>>> sd: SequenceDictionary
>>> with pysam.AlignmentFile("./tests/fgpyo/sam/data/valid.sam") as fh:
...     sd = SequenceDictionary.from_sam(fh.header)
>>> print(sd)  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr1	LN:101
@SQ	SN:chr2	LN:101
@SQ	SN:chr3	LN:101
@SQ	SN:chr4	LN:101
@SQ	SN:chr5	LN:101
@SQ	SN:chr6	LN:101
@SQ	SN:chr7	LN:404
@SQ	SN:chr8	LN:202

```

Query based on index:

```python
>>> print(sd[3])  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr4	LN:101

```

Query based on name:

```python
>>> print(sd["chr6"])  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr6	LN:101

```

Add, get, and delete attributes:

```python
>>> from fgpyo.fasta.sequence_dictionary import Keys
>>> meta = sd[0]
>>> print(meta)  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr1	LN:101
>>> meta[Keys.ASSEMBLY] = "hg38"
>>> print(meta)  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr1	LN:101	AS:hg38
>>> meta.get(Keys.ASSEMBLY)
'hg38'
>>> meta.get(Keys.SPECIES) is None
True
>>> Keys.MD5 in meta
False
>>> del meta[Keys.ASSEMBLY]
>>> print(meta)  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr1	LN:101

```

Get a sequence based on one of its aliases

```python
>>> meta[Keys.ALIASES] = "foo,bar,car"
>>> sd = SequenceDictionary(infos=[meta] + sd.infos[1:])
>>> print(sd)  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr1	LN:101	AN:foo,bar,car
@SQ	SN:chr2	LN:101
@SQ	SN:chr3	LN:101
@SQ	SN:chr4	LN:101
@SQ	SN:chr5	LN:101
@SQ	SN:chr6	LN:101
@SQ	SN:chr7	LN:404
@SQ	SN:chr8	LN:202
>>> print(sd["chr1"])  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr1	LN:101	AN:foo,bar,car
>>> print(sd["bar"])  # doctest: +NORMALIZE_WHITESPACE
@SQ	SN:chr1	LN:101	AN:foo,bar,car

```

Create a `pysam.AlignmentHeader` from a sequence dictionary:

```python
>>> sd.to_sam_header()  # doctest: +ELLIPSIS
<pysam.libcalignmentfile.AlignmentHeader object at ...>
>>> print(sd.to_sam_header())  # doctest: +NORMALIZE_WHITESPACE
@HD	VN:1.5
@SQ	SN:chr1	LN:101	AN:foo,bar,car
@SQ	SN:chr2	LN:101
@SQ	SN:chr3	LN:101
@SQ	SN:chr4	LN:101
@SQ	SN:chr5	LN:101
@SQ	SN:chr6	LN:101
@SQ	SN:chr7	LN:404
@SQ	SN:chr8	LN:202

```

Create a `pysam.AlignmentHeader` from a sequence dictionary with extra header items:

```python
>>> sd.to_sam_header(
...     extra_header={"RG": [{"ID": "A", "LB": "a-library"}, {"ID": "B", "LB": "b-library"}]}
... )  # doctest: +ELLIPSIS
<pysam.libcalignmentfile.AlignmentHeader object at ...>
>>> print(sd.to_sam_header(
...     extra_header={"RG": [{"ID": "A", "LB": "a-library"}, {"ID": "B", "LB": "b-library"}]}
... ))  # doctest: +NORMALIZE_WHITESPACE
@HD	VN:1.5
@SQ	SN:chr1	LN:101	AN:foo,bar,car
@SQ	SN:chr2	LN:101
@SQ	SN:chr3	LN:101
@SQ	SN:chr4	LN:101
@SQ	SN:chr5	LN:101
@SQ	SN:chr6	LN:101
@SQ	SN:chr7	LN:404
@SQ	SN:chr8	LN:202
@RG	ID:A	LB:a-library
@RG	ID:B	LB:b-library

```
"""

import copy
import itertools
import re
import sys
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from enum import unique
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Mapping
from typing import MutableMapping
from typing import Pattern
from typing import overload

from fgpyo import sam

if sys.version_info[:2] < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum

import pysam


@unique
class Topology(StrEnum):
    """Enumeration for the topology of reference sequences (SAM @SQ.TP)"""

    LINEAR = "LINEAR"
    CIRCULAR = "CIRCULAR"


@unique
class Keys(StrEnum):
    """Enumeration of tags/attributes available on a sequence record/metadata (SAM @SQ line)."""

    ALIASES = "AN"
    ALTERNATE_LOCUS = "AH"
    ASSEMBLY = "AS"
    DESCRIPTION = "DS"
    SEQUENCE_LENGTH = "LN"
    MD5 = "M5"
    SEQUENCE_NAME = "SN"
    SPECIES = "SP"
    TOPOLOGY = "TP"
    URI = "UR"

    @staticmethod
    def attributes() -> List[str]:
        """The list of keys that are allowed to be attributes in `SequenceMetadata`.  Notably
        `SEQUENCE_LENGTH` and `SEQUENCE_NAME` are not allowed."""
        return [key for key in Keys if key != Keys.SEQUENCE_NAME and key != Keys.SEQUENCE_LENGTH]


@dataclass(frozen=True, init=True)
class AlternateLocus:
    """Stores an alternate locus for an associated sequence (1-based inclusive)"""

    name: str
    start: int
    end: int

    def __post_init__(self) -> None:
        """Any post initialization validation should go here"""
        if self.start > self.end:
            raise ValueError(f"start > end: {self.start} > {self.end}")
        if self.start < 1:
            raise ValueError(f"start < 1: {self.start}")

    def __str__(self) -> str:
        return f"{self.name}:{self.start}-{self.end}"

    def __len__(self) -> int:
        return self.end - self.start + 1

    @staticmethod
    def parse(value: str) -> "AlternateLocus":
        """Parse the genomic interval of format: `<contig>:<start>-<end>`"""
        name, rest = value.split(":", maxsplit=1)
        start, end = rest.split("-", maxsplit=1)
        return AlternateLocus(name=name, start=int(start), end=int(end))


SEQUENCE_NAME_PATTERN: Pattern = re.compile(
    "^[0-9A-Za-z!#$%&+./:;?@^_|~-][0-9A-Za-z!#$%&*+./:;=?@^_|~-]*$"
)
"""Regular expression for valid reference sequence names according to the SAM spec"""


@dataclass(frozen=True, init=True)
class SequenceMetadata(MutableMapping[Keys | str, str]):
    """Stores information about a single Sequence (ex. chromosome, contig).

    Implements the mutable mapping interface, which provides access to the attributes of this
    sequence, including name, length, but not index.  When using the mapping interface, for example
    getting, setting, deleting, as well as iterating over keys, values, and items, the _values_ will
    always be strings (`str` type).  For example, the length will be an `str` when accessing via
    `get`; access the length directly or use `len` to return an `int`.  Similarly, use the
    `alias` property to return a `List[str]` of aliases, use the `alternate` property to return
    an `AlternativeLocus`-typed instance, and `topology` property to return a `Toplogy`-typed
    instance.

    All attributes except name and length may be set.  Use `dataclasses.replace` to create a new
    copy in such cases.

    Important: The `len` method returns the length of the sequence, not the length of the
    attributes.  Use `len(meta.attributes)` for the latter.

    Attributes:
      name: the primary name of the sequence
      length: the length of the sequence, or zero if unknown
      index: the index in the sequence dictionary
      attributes: attributes of this sequence
    """

    name: str
    length: int
    index: int
    attributes: Dict[Keys | str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Any post initialization validation should go here"""
        if self.length < 0:
            raise ValueError(f"Length must be >= 0 for '{self.name}'")
        if re.search(SEQUENCE_NAME_PATTERN, self.name) is None:
            raise ValueError(f"Illegal name: '{self.name}'")
        if Keys.SEQUENCE_NAME in self.attributes:
            raise ValueError(f"'{Keys.SEQUENCE_NAME}' should not given in the list of attributes")
        if Keys.SEQUENCE_LENGTH in self.attributes:
            raise ValueError(f"'{Keys.SEQUENCE_LENGTH}' should not given in the list of attributes")

    @property
    def aliases(self) -> List[str]:
        """The aliases (not including the primary) name"""
        aliases = self.attributes.get(Keys.ALIASES)
        return [] if aliases is None else aliases.split(",")

    @property
    def all_names(self) -> List[str]:
        """A list of all names, including the primary name and aliases, in that order."""
        return [self.name] + self.aliases

    @property
    def alternate(self) -> AlternateLocus | None:
        """Gets the alternate locus for this sequence"""
        if Keys.ALTERNATE_LOCUS not in self.attributes:
            return None
        value = self.attributes[Keys.ALTERNATE_LOCUS]
        if value == "*":
            return None
        locus = AlternateLocus.parse(value)
        if locus.name == "=":
            locus = replace(locus, name=self.name)
        return locus

    @property
    def is_alternate(self) -> bool:
        """True if there is an alternate locus defined, False otherwise"""
        return self.alternate is not None

    @property
    def md5(self) -> str | None:
        return self.get(Keys.MD5)

    @property
    def assembly(self) -> str | None:
        return self.get(Keys.ASSEMBLY)

    @property
    def uri(self) -> str | None:
        return self.get(Keys.URI)

    @property
    def species(self) -> str | None:
        return self.get(Keys.SPECIES)

    @property
    def description(self) -> str | None:
        return self.get(Keys.DESCRIPTION)

    @property
    def topology(self) -> Topology | None:
        value = self.get(Keys.TOPOLOGY)
        return None if value is None else Topology[value]

    def same_as(self, other: "SequenceMetadata") -> bool:
        """Returns true if the sequences share a common reference name (including aliases), have
        the same length, and the same MD5 if both have MD5s."""
        if self.length != other.length:
            return False
        elif self.name != other.name and other.name not in self.all_names:
            return False
        self_m5 = self.md5
        other_m5 = other.md5
        if self_m5 is None or other_m5 is None:
            return True
        else:
            return self_m5 == other_m5

    def to_sam(self) -> Dict[str, Any]:
        """Converts the sequence metadata to a dictionary equivalent to one item in the
        list of sequences from `pysam.AlignmentHeader#to_dict()["SQ"]`."""
        meta_dict: Dict[str, Any] = {
            f"{Keys.SEQUENCE_NAME}": self.name,
            f"{Keys.SEQUENCE_LENGTH}": self.length,
        }
        if len(self.attributes) > 0:
            meta_dict = {**meta_dict, **self.attributes}

        return meta_dict

    @staticmethod
    def from_sam(meta: Dict[Keys | str, Any], index: int) -> "SequenceMetadata":
        """Builds a `SequenceMetadata` from a dictionary.  The keys must include the sequence
        name (`Keys.SEQUENCE_NAME`) and length (`Keys.SEQUENCE_LENGTH`).  All other keys from
        `Keys` will be stored in the resulting attributes.

        Args:
            meta: the python dictionary with keys from `Keys`.  This is typically the dictionary
                  stored in the `"SQ"` level of the two-level dictionary returned by the
                  `pysam.AlignmentHeader#to_dict()` method.
            index: the 0-based index to use for this sequence
        """
        name = meta[Keys.SEQUENCE_NAME]
        length = meta[Keys.SEQUENCE_LENGTH]
        attributes = copy.deepcopy(meta)
        del attributes[Keys.SEQUENCE_NAME]
        del attributes[Keys.SEQUENCE_LENGTH]
        return SequenceMetadata(name=name, length=length, index=index, attributes=attributes)

    def __getitem__(self, key: Keys | str) -> Any:
        if key == Keys.SEQUENCE_NAME.value:
            return self.name
        elif key == Keys.SEQUENCE_LENGTH.value:
            return f"{self.length}"
        return self.attributes[key]

    def __setitem__(self, key: Keys | str, value: str) -> None:
        if key == Keys.SEQUENCE_NAME or key == Keys.SEQUENCE_LENGTH:
            raise KeyError(f"Cannot set '{key}' on SequenceMetadata with name '{self.name}'")
        self.attributes[key] = value

    def __delitem__(self, key: Keys | str) -> None:
        if key == Keys.SEQUENCE_NAME or key == Keys.SEQUENCE_LENGTH:
            raise KeyError(f"Cannot delete '{key}' on SequenceMetadata with name '{self.name}'")
        del self.attributes[key]

    def __iter__(self) -> Iterator[Keys | str]:
        pre_iter = iter((Keys.SEQUENCE_NAME, Keys.SEQUENCE_LENGTH))
        return itertools.chain(pre_iter, iter(self.attributes))

    def __len__(self) -> int:
        return self.length

    def __str__(self) -> str:
        return "@SQ\t" + "\t".join(f"{key}:{value}" for key, value in self.to_sam().items())

    def __index__(self) -> int:
        return self.index


@dataclass(frozen=True, init=True)
class SequenceDictionary(Mapping[str | int, SequenceMetadata]):
    """Contains an ordered collection of sequences.

    A specific `SequenceMetadata` may be retrieved by name (`str`) or index (`int`), either by
    using the generic `get` method or by the correspondingly named `by_name` and `by_index` methods.
    The latter methods provide faster retrieval when the type is known.

    This _mapping_ collection iterates over the _keys_.  To iterate over each `SequenceMetadata`,
    either use the typical `values()` method or access the metadata directly with `infos`.

    Attributes:
        infos: the ordered collection of sequence metadata
    """

    infos: List[SequenceMetadata]
    _dict: Dict[str, SequenceMetadata] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Initialize a mapping from sequence name to the sequence metadata for all names
        self_dict: Dict[str, SequenceMetadata] = {}
        for index, info in enumerate(self.infos):
            if info.index != index:
                raise ValueError(
                    "Infos must be given with index set correctly."
                    + f"  See ${index}th with name: {info.name}"
                )
            for name in info.all_names:
                if name in self_dict:
                    raise ValueError(f"Found duplicate sequence name: {name}")
                self_dict[name] = info
        object.__setattr__(self, "_dict", self_dict)

    def same_as(self, other: "SequenceDictionary") -> bool:
        """Returns true if the sequences share a common reference name (including aliases), have
        the same length, and the same MD5 if both have MD5s"""
        if len(self) != len(other):
            return False
        return all(this.same_as(that) for this, that in zip(self.infos, other.infos, strict=True))

    def to_sam(self) -> List[Dict[str, Any]]:
        """Converts the list of dictionaries, one per sequence."""
        return [meta.to_sam() for meta in self.infos]

    def to_sam_header(
        self,
        extra_header: Dict[str, Any] | None = None,
    ) -> pysam.AlignmentHeader:
        """Converts the sequence dictionary to a `pysam.AlignmentHeader`.

        Args:
            extra_header: a dictionary of extra values to add to the header, None otherwise.  See
                          `:~pysam.AlignmentHeader` for more details.
        """
        header_dict: Dict[str, Any] = {
            "HD": {"VN": "1.5"},
            "SQ": self.to_sam(),
        }
        if extra_header is not None:
            header_dict = {**header_dict, **extra_header}
        return pysam.AlignmentHeader.from_dict(header_dict=header_dict)

    @staticmethod
    @overload
    def from_sam(data: Path) -> "SequenceDictionary": ...

    @staticmethod
    @overload
    def from_sam(data: pysam.AlignmentFile) -> "SequenceDictionary": ...

    @staticmethod
    @overload
    def from_sam(data: pysam.AlignmentHeader) -> "SequenceDictionary": ...

    @staticmethod
    @overload
    def from_sam(data: List[Dict[str, Any]]) -> "SequenceDictionary": ...

    @staticmethod
    def from_sam(
        data: Path | pysam.AlignmentFile | pysam.AlignmentHeader | List[Dict[str, Any]],
    ) -> "SequenceDictionary":
        """Creates a `SequenceDictionary` from a SAM file or its header.

        Args:
            data: The input may be any of:
                - a path to a SAM file
                - an open `pysam.AlignmentFile`
                - the `pysam.AlignmentHeader` associated with a `pysam.AlignmentFile`
                - the contents of a header's `SQ` fields, as returned by `AlignmentHeader.to_dict()`
        Returns:
            A `SequenceDictionary` mapping refrence names to their metadata.
        """
        seq_dict: SequenceDictionary
        if isinstance(data, pysam.AlignmentHeader):
            seq_dict = SequenceDictionary.from_sam(data.to_dict()["SQ"])
        elif isinstance(data, pysam.AlignmentFile):
            seq_dict = SequenceDictionary.from_sam(data.header.to_dict()["SQ"])
        elif isinstance(data, Path):
            with sam.reader(data) as fh:
                seq_dict = SequenceDictionary.from_sam(fh.header)
        else:  # assuming `data` is a `list[dict[str, Any]]`
            try:
                infos: List[SequenceMetadata] = [
                    SequenceMetadata.from_sam(meta=meta, index=index)
                    for index, meta in enumerate(data)
                ]
                seq_dict = SequenceDictionary(infos=infos)
            except Exception as e:
                raise ValueError(f"Could not parse sequence information from data: {data}") from e

        return seq_dict

    def __getitem__(self, key: str | int) -> SequenceMetadata:
        return self._dict[key] if isinstance(key, str) else self.infos[key]

    def get_by_name(self, name: str) -> SequenceMetadata | None:
        """Gets a `SequenceMetadata` explicitly by `name`.  Returns None if
        the name does not exist in this dictionary"""
        return self._dict.get(name)

    def by_name(self, name: str) -> SequenceMetadata:
        """Gets a `SequenceMetadata` explicitly by `name`.  The name must exist."""
        return self._dict[name]

    def by_index(self, index: int) -> SequenceMetadata:
        """Gets a `SequenceMetadata` explicitly by `name`.  Raises an `IndexError`
        if the index is out of bounds."""
        return self.infos[index]

    def __iter__(self) -> Iterator[str]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self.infos)

    def __str__(self) -> str:
        return "\n".join(f"{info}" for info in self.infos)
