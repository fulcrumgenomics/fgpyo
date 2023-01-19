"""Basic tests for io module"""

import io
import os
from pathlib import Path
from tempfile import NamedTemporaryFile as NamedTemp
from typing import Any
from typing import List

import pytest
from pytest import raises

import fgpyo.io.io as IO


def test_paths_are_readable_missing_file_error() -> None:
    """Error when file does not exist"""
    path = Path("error.txt")
    with raises(AssertionError):
        IO.paths_are_readable(path=path)


def test_paths_are_readable_mode_error() -> None:
    """Error when permissions are write only by owner"""
    with NamedTemp(suffix=".txt", mode="r", delete=True) as write_file:
        path = Path(write_file.name)
        os.chmod(path, 0o00200)  # Write only permissions
        with raises(AssertionError):
            IO.paths_are_readable(path=path)


def test_paths_are_readable_pass() -> None:
    """Returns none when no assertions are violated"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        IO.paths_are_readable(path=path)


def test_directory_exists_error() -> None:
    """Ensure OSError when directory does not exist"""
    path = Path("/non/existant/dir/")
    with raises(AssertionError):
        IO.directory_exists(path)


def test_directory_exists_pass() -> None:
    """Asserts IO._directory_exists() returns True when directory exists"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        IO.directory_exists(path=path.parent.absolute())


def test_paths_are_writeable_mode_error() -> None:
    """Error when permissions are read only by owner"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as read_file:
        path = Path(read_file.name)
        os.chmod(path, 0o00400)  # Read only permissions
        raises(AssertionError, IO.paths_are_writeable, path)


def test_paths_are_writeable_pass() -> None:
    """Error when permissions are read only by owner"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as read_file:
        path = Path(read_file.name)
        IO.paths_are_writeable(path=path) is True


@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".gz", io._io.TextIOWrapper),
        (".fa", io._io.TextIOWrapper),
    ],
)
def test_reader(
    suffix: str,
    expected: Any,
) -> None:
    """Tests fgpyo.io.io.to_reader"""
    with NamedTemp(suffix=suffix, mode="r", delete=True) as read_file:
        reader = IO.to_reader(path=Path(read_file.name))
        assert isinstance(reader, expected)
        reader.close()


@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".gz", io._io.TextIOWrapper),
        (".fa", io._io.TextIOWrapper),
    ],
)
def test_writer(
    suffix: str,
    expected: Any,
) -> None:
    """Tests fgpyo.io.io.to_writer()"""
    with NamedTemp(suffix=suffix, mode="w", delete=True) as write_file:
        writer = IO.to_writer(path=Path(write_file.name))
        assert isinstance(writer, expected)
        writer.close()


@pytest.mark.parametrize(
    "suffix, list_to_write",
    [(".txt", ["Test with a flat file", 10]), (".gz", ["Test with a gzip file", 10])],
)
def test_read_and_write_lines(
    suffix: str,
    list_to_write: List[Any],
) -> None:
    """Test fgpyo.io.io.read_lines and write_lines"""
    with NamedTemp(suffix=suffix, mode="wb", delete=True) as read_file:
        IO.write_lines(path=Path(read_file.name), lines_to_write=list_to_write)
        read_back = IO.read_lines(path=Path(read_file.name))
        assert read_back == [str(item) for item in list_to_write]
