"""
# Module for reading and writing files

The functions in this module make it easy to:

* check if a file exists and is writable
* check if a file and its parent directories exist and are writable
* check if a file exists and is readable
* check if a path exists and is a directory
* open an appropriate reader or writer based on the file extension
* write items to a file, one per line
* read lines from a file

## fgpyo.io Examples:

```python

    >>> import fgpyo.io as fio
    >>> from pathlib import Path
    Assert that a path exists and is readable
    >>> path_flat: Path = Path("example.txt")
    >>> path_compressed: Path = Path("example.txt.gz")
    >>> fio.path_is_readable(path_flat)
    AssertionError: Cannot read non-existent path: example.txt
    >>> fio.path_is_readable(compressed_file)
    AssertionError: Cannot read non-existent path: example.txt.gz
    Write to and read from path
    >>> write_lines(path = path_flat, lines_to_write=["flat file", 10])
    >>> write_lines(path = path_compressed, lines_to_write=["gzip file", 10])
    Read lines from a path into a generator
    >>> lines = read_lines(path = path_flat)
    >>> next(lines)
    "flat file"
    >>> next(lines)
    "10"
    >>> lines = read_lines(path = path_compressed)
    >>> next(lines)
    "gzip file"
    >>> next(lines)
    "10"
```

"""

import gzip
import os
import sys
import warnings
from contextlib import contextmanager
from io import TextIOWrapper
from pathlib import Path
from typing import IO
from typing import Any
from typing import Generator
from typing import Iterable
from typing import Iterator
from typing import Set
from typing import cast

COMPRESSED_FILE_EXTENSIONS: Set[str] = {".gz", ".bgz"}


def assert_path_is_readable(path: Path) -> None:
    """Checks that file exists and returns True, else raises AssertionError

    Args:
        path: a Path to check

    Example:
        assert_file_exists(path = Path("some_file.csv"))
    """
    # stdin is readable
    if path == Path("/dev/stdin"):
        return

    assert path.exists(), f"Cannot read non-existent path: {path}"
    assert path.is_file(), f"Cannot read path becasue it is not a file: {path}"
    assert os.access(path, os.R_OK), f"Path exists but is not readable: {path}"


def assert_directory_exists(path: Path) -> None:
    """Asserts that a path exist and is a directory

    Args:
        path: Path to check

    Example:
        assert_directory_exists(path = Path("/example/directory/"))
    """
    assert path.exists(), f"Path does not exist: {path}"
    assert path.is_dir(), f"Path exists but is not a directory: {path}"


def assert_path_is_writeable(path: Path, parent_must_exist: bool = True) -> None:
    """
    A deprecated alias for `assert_path_is_writable()`.
    """
    warnings.warn(
        "assert_path_is_writeable is deprecated, use assert_path_is_writable instead",
        DeprecationWarning,
        stacklevel=2,
    )

    assert_path_is_writable(path=path, parent_must_exist=parent_must_exist)


def assert_path_is_writable(path: Path, parent_must_exist: bool = True) -> None:
    """
    Assert that a filepath is writable.

    Specifically:
    - If the file exists then it must also be writable.
    - Else if the path is not a file and `parent_must_exist` is true, then assert that the parent
      directory exists and is writable.
    - Else if the path is not a directory and `parent_must_exist` is false, then look at each parent
      directory until one is found that exists and is writable.

    Args:
        path: Path to check
        parent_must_exist: If True, the file's parent directory must exist. Otherwise, at least one
            directory in the path's components must exist.

    Raises:
        AssertionError: If any of the above conditions are not met.

    Example:
        assert_path_is_writable(path = Path("example.txt"))
    """
    # stdout is writable
    if path == Path("/dev/stdout"):
        return

    # If path exists, it must be a writable file
    if path.exists():
        assert path.is_file(), f"Cannot read path becasue it is not a file: {path}"
        assert os.access(path, os.W_OK), f"File exists but is not writable: {path}"

    # Else if file doesnt exist and parent_must_exist is True then check
    # that path.absolute().parent exists, is a directory and is writable
    elif parent_must_exist:
        parent = path.absolute().parent
        assert parent.exists(), f"Parent directory does not exist: {parent}"
        assert parent.is_dir(), f"Parent directory exists but is not a directory: {parent}"
        assert os.access(parent, os.W_OK), f"Parent directory exists but is not writable: {parent}"

    # Else if file doesn't exist and parent_must_exist is False, test parent until
    # you find the first extant path, and check that it is a directory and is writable.
    else:
        for parent in path.absolute().parents:
            if parent.exists():
                assert os.access(parent, os.W_OK), f"Parent directory is not writable: {parent}"
                break
        else:
            raise AssertionError(f"No parent directories exist for: {path}")


def to_reader(path: Path) -> TextIOWrapper:
    """Opens a Path for reading and based on extension uses open() or gzip.open()

    Args:
        path: Path to read from

    Example:
        >>> reader = fio.to_reader(path = Path("reader.txt"))
        >>> reader.readlines()
        >>> reader.close()

    """
    if path.suffix in COMPRESSED_FILE_EXTENSIONS:
        return TextIOWrapper(cast(IO[bytes], gzip.open(path, mode="rb")), encoding="utf-8")
    else:
        return path.open(mode="r")


def to_writer(path: Path, append: bool = False) -> TextIOWrapper:
    """Opens a Path for writing (or appending) and based on extension uses open() or gzip.open()

    Args:
        path: Path to write (or append) to

    Example:
        >>> writer = fio.to_writer(path = Path("writer.txt"))
        >>> writer.write(f'{something}\\n')
        >>> writer.close()

    """
    mode_prefix: str = "a" if append else "w"

    if path.suffix in COMPRESSED_FILE_EXTENSIONS:
        return TextIOWrapper(
            cast(IO[bytes], gzip.open(path, mode=mode_prefix + "b")), encoding="utf-8"
        )
    else:
        # NB: the `cast` here is necessary because `path.open()` may return
        # other types, depending on the specified `mode`.
        # Within the scope of this function, `mode_prefix` is guaranteed to be
        # either "w" or "a", both of which result in a `TextIOWrapper`, but
        # mypy can't follow that logic.
        return cast(TextIOWrapper, path.open(mode=mode_prefix))


def read_lines(path: Path, strip: bool = False) -> Iterator[str]:
    """Takes a path and reads each line into a generator, removing line terminators
    along the way. By default only line terminators (CR/LF) are stripped.  The `strip`
    parameter may be used to strip both leading and trailing whitespace from each line.

    Args:
        path: Path to read from
        strip: True to strip lines of all leading and trailing whitespace,
            False to only remove trailing CR/LF characters.

    Example:
        read_back = fio.read_lines(path)
    """
    with to_reader(path=path) as reader:
        if strip:
            for line in reader:
                yield line.strip()
        else:
            for line in reader:
                yield line.rstrip("\r\n")


def write_lines(path: Path, lines_to_write: Iterable[Any], append: bool = False) -> None:
    """Writes (or appends) a file with one line per item in provided iterable

    Args:
        path: Path to write (or append) to
        lines_to_write: items to write (or append) to file

    Example:
        lines: List[Any] = ["things to write", 100]
        path_to_write_to: Path = Path("file_to_write_to.txt")
        fio.write_lines(path = path_to_write_to, lines_to_write = lines)
    """
    with to_writer(path=path, append=append) as writer:
        for line in lines_to_write:
            writer.write(str(line))
            writer.write("\n")


@contextmanager
def redirect_to_dev_null(file_num: int) -> Generator[None, None, None]:
    """A context manager that redirects output of file handle to /dev/null

    Args:
        file_num: number of filehandle to redirect.
    """
    # open /dev/null for writing
    f_devnull = os.open(os.devnull, os.O_RDWR)
    # save old file descriptor and redirect stderr to /dev/null
    save_stderr = os.dup(file_num)
    os.dup2(f_devnull, file_num)

    yield

    # restore file descriptor and close devnull
    os.dup2(save_stderr, file_num)
    os.close(f_devnull)


@contextmanager
def suppress_stderr() -> Generator[None, None, None]:
    """A context manager that redirects output of stderr to /dev/null"""
    with redirect_to_dev_null(file_num=sys.stderr.fileno()):
        yield


def assert_fasta_indexed(
    fasta: Path,
    /,
    dictionary: bool = False,
    bwa: bool = False,
) -> None:
    """
    Verify that a FASTA is readable and has the expected index files.

    The existence of the FASTA index generated by `samtools faidx` will always be verified. The
    existence of the index files generated by `samtools dict` and `bwa index` may be optionally
    verified.

    Args:
        fasta: Path to the FASTA file.
        dictionary: If True, check for the index file generated by `samtools dict` (`{fasta}.dict`).
        bwa: If True, check for the index files generated by `bwa index` (`{fasta}.{suffix}`, for
            all suffixes in ["amb", "ann", "bwt", "pac", "sa"]).

    Raises:
        AssertionError: If the FASTA or any of the expected index files are missing or not readable.
    """
    fai_index = Path(f"{fasta}.fai")
    assert_path_is_readable(fai_index)

    if dictionary:
        dict_index = Path(f"{fasta}.dict")
        assert_path_is_readable(dict_index)

    if bwa:
        suffixes = ["amb", "ann", "bwt", "pac", "sa"]
        for suffix in suffixes:
            bwa_index = Path(f"{fasta}.{suffix}")
            assert_path_is_readable(bwa_index)
