"""
IO
-------
Module for reading and writing files.

The functions in this module make is easy to:
    check if a file exists and is writeable
    check if a file and its parent directories exist and are writeable
    check if a file exists and is readable
    check if a path exists and is a directory
    open an appropriate reader or writer based on the file extension
    writitng items to a file
    reading lines from a file
~~~~~~~~
Examples:
.. code-block:: python
   >>> import fgpyo.io.io as IO
   >>> from pathlib import Path
   Assert that paths exist and are readable
   >>> path_flath: Path = Path("example.txt")
   >>> path_compressed: Path = Path("example.txt.gz")
   >>> IO.paths_are_readable(path_flat)
   AssertionError: Cannot read non-existent path: example.txt
   >>> IO.paths_are_readable(compressed_file)
   AssertionError: Cannot read non-existent path: example.txt.gz
   Write to and read from path
   >>> write_lines(path = path_flat, lines_to_write=["flat file", 10])
   >>> write_lines(path = path_compressed, lines_to_write=["gzip file", 10])
   Read lines from paths into a list of strings
   >>> read_lines(path = path_flat)
   ['flat file', '10']
   >>> read_lines(path = path_compressed)
   ['gzip file', '10']
"""

import gzip
import os
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Set

COMPRESSED: Set[str] = {".gz", ".bgz"}


def paths_are_readable(path: Path) -> None:
    """Checks that file exists and returns True, else raises FileNotFoundError

    Args:
        paths: a list of one or more Paths to be investigated

    Example:
    _file_exists(path = Path("some_file.csv"))
    """
    assert path.exists() is True, f"Cannot read non-existent path: {path}"
    assert path.is_dir() is False, f"Cannot read path becasue it is a directory: {path}"
    assert os.access(path, os.R_OK) is True, f"Path exists but is not readable: {path}"


def directory_exists(path: Path) -> None:
    """Asserts one or more Paths exist and are directories

    Args:
        paths: list of one or more Paths to be investigated

    Example:
    _directory_exists(path = Path("/example/directory/"))
    """
    assert path.exists() is True, f"Path does not exist: {path}"
    assert path.is_dir() is True, f"Path exists but is not a directory: {path}"


def paths_are_writeable(path: Path, parent_must_exist: bool = True) -> None:
    """Checks that path is writable and returns True, else raises an Exception
    Args:
         path: Path to be investigated
    Example:
    _writeable(path = Path("example.txt"))
    """
    assert path.exists() is True, f"Cannot write file because path is non-existent: {path}"
    assert path.is_file() is True, f"Cannot write file because path is a directory: {path}"
    assert os.access(path, os.W_OK) is True, f"File exists but is not writebale: {path}"

    if parent_must_exist:
        parent: str = f"{path.parent.absolute()}"
        assert (
            Path(parent).exists() is True
        ), f"Cannot write file because parent diretory does not exist: {path}"
        assert (
            Path(parent).is_dir() is True
        ), f"Cannot write file because parent exists and is not a directory: {path}"
        assert (
            os.access(parent, os.W_OK) is True
        ), f"Cannot write file because parent directory is not writeable: {path}"


def to_reader(path: Path, mode: str = "rt") -> Any:
    # TODO find compatible return type
    """Opens a Path for reading with a specifeied mode or default 'rt'.

    Args:
        path: Path to be read from
        mode: Mode to open reader, default 'rt'

    Example:
    >>> reader = io.to_reader(path = Path("reader.txt"))
    >>> reader.readlines()
    >>> reader.close()
    """
    if path.suffix in COMPRESSED:
        return gzip.open(path, mode=mode)
    else:
        return path.open(mode=mode)


def to_writer(path: Path, mode: str = "wt") -> Any:
    # TODO find compatible return type
    """Opens a Path for reading and based on extension uses open() or gzip.open()

    Args:
        path: Path to write to
        mode: Mode to open writer, default 'wt'

    Example:
    >>> writer = io.to_writer(path = Path("writer.txt"))
    >>> writer.write(f"{something}\n")
    >>> writer.close()
    """
    if path.suffix in COMPRESSED:
        return gzip.open(path, mode=mode)
    else:
        return path.open(mode=mode)


def read_lines(path: Path, strip: bool = True) -> Any:
    """Takes a path and reads it into a list of strings, removing line terminators
    along the way.
    # TODO Make line strip optional

    Args:
        path: Path to read from
        strip: Boolean to strip lines or not

    Example:
    >>> read_back: List[str] = io.read_lines(path)
    """
    reader = to_reader(path=path)
    list_of_lines = reader.readlines()
    reader.close()
    if strip:
        return [line.strip() for line in list_of_lines]
    else:
        return [line.replace("\n", "") for line in list_of_lines]


def write_lines(path: Path, lines_to_write: Iterable[Any]) -> None:
    """Writes a file with one line per item in provided iterable

    Args:
        path: Path to write to
        lines_to_write: items to write to file

    Example:
    >>> lines: List[Any] = ["things to write", 100]
    >>> path: Path = Path("file_to_write_to.txt")
    >>> io.write_lines(path = path, lines_to_write = lines)
    """
    writer = to_writer(path=path)
    writer.writelines([f"{item}\n" for item in lines_to_write])
    writer.close()
