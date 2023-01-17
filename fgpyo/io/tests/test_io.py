"""Basic tests for io module"""

import gzip
import io
import os
from pathlib import Path
from tempfile import NamedTemporaryFile as NamedTemp
from typing import Any
from typing import List

import pytest
from pytest import raises

from fgpyo.io.io import IO


def test_file_exists_error() -> None:
    """Ensure FileNotFoundError"""
    path = Path("error.txt")
    test_io = IO([path])
    with raises(FileNotFoundError):
        test_io._file_exists(path)


def test_file_exists_True() -> None:
    """Asserts IO._file_exists() returns True when file exists"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        test_io = IO([path])
        assert test_io._file_exists(path=path) is True


def test_dir_exists_error() -> None:
    """Ensure OSError when directory does not exist"""
    path = Path("/non/existant/dir/")
    test_io = IO([path])
    with raises(NotADirectoryError):
        test_io._directory_exists(path)


def test_dir_exists_True() -> None:
    """Asserts IO._directory_exists() returns True when directory exists"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        test_io = IO([path])
        assert test_io._directory_exists(path=path.parent.absolute()) is True


def test_readable_error() -> None:
    """Error when permissions are write only by owner"""
    with NamedTemp(suffix=".txt", mode="r", delete=True) as write_file:
        path = Path(write_file.name)
        test_io = IO([path])
        os.chmod(path, 0o00200)  # Write only permissions
        with raises(Exception):
            test_io._readable(path=path)


def test_readable_True() -> None:
    """Error when permissions are write only by owner"""
    with NamedTemp(suffix=".txt", mode="r", delete=True) as write_file:
        path = Path(write_file.name)
        test_io = IO([path])
        assert test_io._readable(path=path) is True


def test_writeable_error() -> None:
    """Error when permissions are read only by owner"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as read_file:
        path = Path(read_file.name)
        test_io = IO([path])
        os.chmod(path, 0o00400)  # Read only permissions
        with raises(Exception):
            test_io._writable(path=path)


def test_writeable_True() -> None:
    """Error when permissions are read only by owner"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as read_file:
        path = Path(read_file.name)
        test_io = IO([path])
        assert test_io._writeable(path=path) is True


@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".gz", gzip.GzipFile),
        (".fa", io._io.TextIOWrapper),
    ],
)
def test_reader(
    suffix: str,
    expected: Any,
) -> None:
    # TODO fix docstring
    """Tests IO.reader"""
    with NamedTemp(suffix=suffix, mode="r", delete=True) as read_file:
        file = IO.reader(path=Path(read_file.name))
        assert isinstance(file, expected)
        file.close()


@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".gz", gzip.GzipFile),
        (".fa", io._io.TextIOWrapper),
    ],
)
def test_writer(
    suffix: str,
    expected: Any,
) -> None:
    # TODO fix docstring
    """Tests IO.writer"""
    # Openfile with file so that tmp file is deleted automatically
    with NamedTemp(suffix=suffix, mode="w", delete=True) as write_file:
        writer_file = IO.writer(path=Path(write_file.name))
        assert isinstance(writer_file, expected)
        writer_file.close()


@pytest.mark.parametrize(
    "suffix, expected",
    [(".txt", ["1", "string"]), (".gz", ["Test with a gzip file", "string"])],
)
def test_read_lines(
    suffix: str,
    expected: List[str],
) -> None:
    """Test IO.read_lines"""

    bytes_suffix = {".gz", ".bgz"}

    with NamedTemp(suffix=suffix, mode="wb", delete=True) as read_file:
        test_IO = IO([Path(read_file.name)])
        with IO.writer(path=Path(read_file.name)) as writer:
            if suffix in bytes_suffix:
                for element in expected:
                    writer.write(bytes(f"{element}\n", "utf-8"))
            else:
                for element in expected:
                    writer.write(f"{element}\n")
        returned = test_IO.read_lines(path=Path(read_file.name))
        assert returned == expected
