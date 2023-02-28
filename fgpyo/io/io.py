"""
IO
-------
Module for reading and writing files.

The functions in this module make is easy to:
* check if a file exists and is writeable
* check if a file and its parent directories exist and are writeable
* check if a file exists and is readable
* check if a path exists and is a directory
* open an appropriate reader or writer based on the file extension
* writitng items to a file
* reading lines from a file
~~~~~~~~
Examples:
.. code-block:: python
   >>> import fgpyo.io.io as IO
   >>> from pathlib import Path
   Assert that a path exist and are readable
   >>> path_flath: Path = Path("example.txt")
   >>> path_compressed: Path = Path("example.txt.gz")
   >>> IO.path_is_readable(path_flat)
   AssertionError: Cannot read non-existent path: example.txt
   >>> IO.path_is_readable(compressed_file)
   AssertionError: Cannot read non-existent path: example.txt.gz
   Write to and read from path
   >>> write_lines(path = path_flat, lines_to_write=["flat file", 10])
   >>> write_lines(path = path_compressed, lines_to_write=["gzip file", 10])
   Read lines from a path into a generator
   >>> read_lines(path = path_flat)
   ['flat file', '10']
   >>> read_lines(path = path_compressed)
   ['gzip file', '10']
"""

import gzip
import io
import os
from pathlib import Path
from typing import IO
from typing import Any
from typing import Generator
from typing import Iterable
from typing import Iterator
from typing import Set
from typing import TextIO
from typing import Union
from typing import cast

COMPRESSED_FILE_EXTENSIONS: Set[str] = {".gz", ".bgz"}


def path_is_readable(path: Path) -> None:
    """Checks that file exists and returns True, else raises FileNotFoundError

    Args:
        path: a Path to check

    Example:
    _file_exists(path = Path("some_file.csv"))
    """
    assert path.exists(), f"Cannot read non-existent path: {path}"
    assert not path.is_dir(), f"Cannot read path becasue it is a directory: {path}"
    assert os.access(path, os.R_OK), f"Path exists but is not readable: {path}"


def directory_exists(path: Path) -> None:
    """Asserts that a path exist and is a directory

    Args:
        path: Path to check

    Example:
    _directory_exists(path = Path("/example/directory/"))
    """
    assert path.exists(), f"Path does not exist: {path}"
    assert path.is_dir(), f"Path exists but is not a directory: {path}"


def path_is_writeable(path: Path, parent_must_exist: bool = True) -> None:
    """Checks that path is writable and returns True, else raises an Exception
    Args:
         path: Path to check
         parent_must_exist: True/False the parent directory must exist, the default is True
    Example:
    _writeable(path = Path("example.txt"))
    """
    assert path.exists(), f"Cannot write file because path is non-existent: {path}"
    assert path.is_file(), f"Cannot write file because path is a directory: {path}"
    assert os.access(path, os.W_OK), f"File exists but is not writebale: {path}"

    if not parent_must_exist:
        return None

    parent: str = f"{path.parent.absolute()}"
    assert Path(
        parent
    ).exists(), f"Cannot write file because parent diretory does not exist: {path}"
    assert Path(
        parent
    ).is_dir(), f"Cannot write file because parent exists and is not a directory: {path}"
    assert os.access(
        parent, os.W_OK
    ), f"Cannot write file because parent directory is not writeable: {path}"


def to_reader(path: Path) -> Union[io.TextIOWrapper, TextIO, IO[Any]]:
    """Opens a Path for reading with a specified mode or default 'rt'.

    Args:
        path: Path to read from

    Example:
    >>> reader = io.to_reader(path = Path("reader.txt"))
    >>> reader.readlines()
    >>> reader.close()
    """
    if path.suffix in COMPRESSED_FILE_EXTENSIONS:
        return io.TextIOWrapper(cast(IO[bytes], gzip.open(path, mode="rb")), encoding="utf-8")
    else:
        return path.open(mode="r")


def to_writer(path: Path) -> Union[IO[Any], io.TextIOWrapper]:
    """Opens a Path for reading and based on extension uses open() or gzip.open()

    Args:
        path: Path to write to

    Example:
    >>> writer = io.to_writer(path = Path("writer.txt"))
    >>> writer.write(f'{something}\n')
    >>> writer.close()
    """
    if path.suffix in COMPRESSED_FILE_EXTENSIONS:
        return io.TextIOWrapper(cast(IO[bytes], gzip.open(path, mode="wb")), encoding="utf-8")
    else:
        return path.open(mode="w")


def read_lines(path: Path, strip: bool = True) -> Union[Iterator[str], Generator[str, None, None]]:
    """Takes a path and reads each line into a generator, removing line terminators
    along the way.

    Args:
        path: Path to read from
        strip: Boolean to strip lines or not

    Example:
    >>> read_back: List[str] = io.read_lines(path)
    """
    with to_reader(path=path) as reader:
        if strip:
            for line in reader:
                yield (f"{line!s}").strip()
        else:
            for line in reader:
                yield f"{line!s}".rstrip("\r\n")


def write_lines(path: Path, lines_to_write: Iterable[Any]) -> None:
    """Writes a file with one line per item in provided iterable

    Args:
        path: Path to write to
        lines_to_write: items to write to file

    Example:
    >>> lines: List[Any] = ["things to write", 100]
    >>> path_to_write_to: Path = Path("file_to_write_to.txt")
    >>> io.write_lines(path = path_to_write_to, lines_to_write = lines)
    """
    with to_writer(path=path) as writer:
        for line in lines_to_write:
            writer.write(f"{line}" + "\n")
