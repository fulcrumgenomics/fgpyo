"""
# Zipping FASTX Files

Zipping a set of FASTA/FASTQ files into a single stream of data is a common task in bioinformatics
and can be achieved with the [`FastxZipped()`][fgpyo.fastx.FastxZipped] context manager.
The context manager facilitates opening of all input FASTA/FASTQ files and closing them after
iteration is complete.  For every iteration of [`FastxZipped()`][fgpyo.fastx.FastxZipped],
a tuple of the next FASTX records are returned (of type
`pysam.FastxRecord()`). An exception will be raised if any of the input
files are malformed or truncated and if record names are not equivalent and in sync.

Importantly, this context manager is optimized for fast streaming read-only usage and, by default,
any previous records saved while advancing the iterator will not be correct as the underlying
pointer in memory will refer to the most recent record only, and not any past records. To preserve
the state of all previously iterated records, set the parameter ``persist`` to `True`.

```python
   >>> from fgpyo.fastx import FastxZipped
   >>> with FastxZipped("r1.fq", "r2.fq", persist=False) as zipped:
   ...    for (r1, r2) in zipped:
   ...         print(f"{r1.name}: {r1.sequence}, {r2.name}: {r2.sequence}")
   seq1: AAAA, seq1: CCCC
   seq2: GGGG, seq2: TTTT
```

"""

from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Iterator
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Type
from typing import Union

from pysam import FastxFile
from pysam import FastxRecord


class FastxZipped(AbstractContextManager, Iterator[Tuple[FastxRecord, ...]]):
    """A context manager that will lazily zip over any number of FASTA/FASTQ files.

    Args:
        paths: Paths to the FASTX files to zip over.
        persist: Whether to persist the state of previous records during iteration.

    """

    def __init__(self, *paths: Union[Path, str], persist: bool = False) -> None:
        """Instantiate a `FastxZipped` context manager and iterator."""
        if len(paths) <= 0:
            raise ValueError(f"Must provide at least one FASTX to {self.__class__.__name__}")
        self._persist: bool = persist
        self._paths: Tuple[Union[Path, str], ...] = paths
        self._fastx = tuple(FastxFile(str(path), persist=self._persist) for path in self._paths)

    @staticmethod
    def _name_minus_ordinal(name: str) -> str:
        """Return the name of the FASTX record minus its ordinal suffix (e.g. "/1" or "/2")."""
        return name[: len(name) - 2] if len(name) >= 2 and name[-2] == "/" else name

    def __next__(self) -> Tuple[FastxRecord, ...]:
        """Return the next set of FASTX records from the zipped FASTX files."""
        records = tuple(next(handle, None) for handle in self._fastx)
        if all(record is None for record in records):
            raise StopIteration
        elif any(record is None for record in records):
            sequence_name: str = [record.name for record in records if record is not None][0]
            raise ValueError(
                "One or more of the FASTX files is truncated for sequence "
                + f"{self._name_minus_ordinal(sequence_name)}:\n\t"
                + "\n\t".join(
                    str(self._paths[i]) for i, record in enumerate(records) if record is None
                )
            )
        else:
            record_names: Set[str] = {self._name_minus_ordinal(record.name) for record in records}
            if len(record_names) != 1:
                raise ValueError(f"FASTX record names do not all match: {record_names}")
            return records

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        """Exit the `FastxZipped` context manager by closing all FASTX files."""
        self.close()
        if exc_type is not None:
            raise exc_type(exc_val).with_traceback(exc_tb)
        return None

    def close(self) -> None:
        """Close the `FastxZipped` context manager by closing all FASTX files."""
        for fastx in self._fastx:
            fastx.close()
