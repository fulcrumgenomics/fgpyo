"""
# Classes for generating VCF and records for testing

This module contains utility classes for the generation of VCF files and variant records, for use
in testing.

The module contains the following public classes:

- [`VariantBuilder()`][fgpyo.vcf.builder.VariantBuilder] -- A builder class that allows the
    accumulation of variant records and access as a list and writing to file.

## Examples

Typically, we have `pysam.VariantRecord` records obtained from reading
from a VCF file.  The [`VariantBuilder()`][fgpyo.vcf.builder.VariantBuilder] class builds
such records.

Variants are added with the [`add()`][fgpyo.vcf.builder.VariantBuilder.add] method,
which returns a `pysam.VariantRecord`.

```python
    >>> import pysam
    >>> from fgpyo.vcf.builder import VariantBuilder
    >>> builder: VariantBuilder = VariantBuilder()
    >>> new_record_1: pysam.VariantRecord = builder.add()  # uses the defaults
    >>> new_record_2: pysam.VariantRecord = builder.add(
    >>>     contig="chr2", pos=1001, id="rs1234", ref="C", alts=["T"],
    >>>     qual=40, filter=["PASS"]
    >>> )
```

VariantBuilder can create sites-only, single-sample, or multi-sample VCF files. If not producing a
sites-only VCF file, VariantBuilder must be created by passing a list of sample IDs

```python
    >>> builder: VariantBuilder = VariantBuilder(sample_ids=["sample1", "sample2"])
    >>> new_record_1: pysam.VariantRecord = builder.add()  # uses the defaults
    >>> new_record_2: pysam.VariantRecord = builder.add(
    >>>     samples={"sample1": {"GT": "0|1"}, "sample2": {"GT": "0|0"}}
    >>> )
```

The variants stored in the builder can be retrieved as a coordinate sorted VCF file via the
[`to_path()`][fgpyo.vcf.builder.VariantBuilder.to_path] method:

```python
    >>>     from pathlib import Path
    >>>     path_to_vcf: Path = builder.to_path()
```

The variants may also be retrieved in the order they were added via the
[`to_unsorted_list()`][fgpyo.vcf.builder.VariantBuilder.to_unsorted_list] method and
in coordinate sorted order via the
[`to_sorted_list()`][fgpyo.vcf.builder.VariantBuilder.to_sorted_list] method.

"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from typing import TextIO
from typing import Union

from pysam import VariantFile
from pysam import VariantFile as VcfReader
from pysam import VariantFile as VcfWriter
from pysam import VariantHeader

import fgpyo.io

"""The valid base classes for opening a VCF file."""
VcfPath = Union[Path, str, TextIO]


@contextmanager
def reader(path: VcfPath) -> Generator[VcfReader, None, None]:
    """Opens the given path for VCF reading

    Args:
        path: the path to a VCF, or an open file handle
    """
    if isinstance(path, (str, Path, TextIO)):
        with fgpyo.io.suppress_stderr():
            # to avoid spamming log about index older than vcf, redirect stderr to /dev/null: only
            # when first opening the file
            _reader = VariantFile(path, mode="r")  # type: ignore[arg-type]
        # now stderr is back, so any later stderr messages will go through
        yield _reader
        _reader.close()
    else:
        raise TypeError(f"Cannot open '{type(path)}' for VCF reading.")


@contextmanager
def writer(path: VcfPath, header: VariantHeader) -> Generator[VcfWriter, None, None]:
    """Opens the given path for VCF writing.

    Args:
        path: the path to a VCF, or an open filehandle
        header: the source for the output VCF header. If you are modifying a VCF file that you are
                reading from, you can pass reader.header
    """
    # Convert Path to str such that pysam will autodetect to write as a gzipped file if provided
    # with a .vcf.gz suffix.
    if isinstance(path, Path):
        path = str(path)
    _writer = VariantFile(path, header=header, mode="w")
    yield _writer
    _writer.close()
