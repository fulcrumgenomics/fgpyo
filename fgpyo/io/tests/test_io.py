"""Basic tests for io module"""

import io
import os
from pathlib import Path
from tempfile import NamedTemporaryFile as NamedTemp
from typing import Any
from typing import List

import pytest
from pytest import raises

import fgpyo.io as IO


def test_assert_path_is_readable_missing_file_error() -> None:
    """Error when file does not exist"""
    path = Path("error.txt")
    with raises(AssertionError):
        IO.assert_path_is_readable(path=path)


def test_assert_path_is_readable_mode_error() -> None:
    """Error when permissions are write only by owner"""
    with NamedTemp(suffix=".txt", mode="r", delete=True) as write_file:
        path = Path(write_file.name)
        os.chmod(path, 0o00200)  # Write only permissions
        with raises(AssertionError):
            IO.assert_path_is_readable(path=path)


def test_assert_path_is_readable_pass() -> None:
    """Returns none when no assertions are violated"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        IO.assert_path_is_readable(path=path)


def test_assert_directory_exists_error() -> None:
    """Ensure OSError when directory does not exist"""
    path = Path("/non/existent/dir/")
    with raises(AssertionError):
        IO.assert_directory_exists(path)


def test_assert_directory_exists_pass() -> None:
    """Asserts IO._assert_directory_exists() returns True when directory exists"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        IO.assert_directory_exists(path=path.parent.absolute())


def test_assert_path_is_writeable_mode_error() -> None:
    """Error when permissions are read only by owner"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as read_file:
        path = Path(read_file.name)
        os.chmod(path, 0o00400)  # Read only permissions
        raises(AssertionError, IO.assert_path_is_writeable, path)


def test_assert_path_is_writeable_pass() -> None:
    """Should return the correct writeable path"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as read_file:
        path = Path(read_file.name)
        assert IO.assert_path_is_writeable(path=path) == path


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
        with IO.to_reader(path=Path(read_file.name)) as reader:
            assert isinstance(reader, expected)


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
        with IO.to_writer(path=Path(write_file.name)) as writer:
            assert isinstance(writer, expected)


@pytest.mark.parametrize(
    "suffix, list_to_write",
    [(".txt", ["Test with a flat file", 10]), (".gz", ["Test with a gzip file", 10])],
)
def test_read_and_write_lines(
    suffix: str,
    list_to_write: List[Any],
) -> None:
    """Test fgpyo.io.io.read_lines and write_lines"""
    with NamedTemp(suffix=suffix, mode="w", delete=True) as read_file:
        IO.write_lines(path=Path(read_file.name), lines_to_write=list_to_write)
        read_back = IO.read_lines(path=Path(read_file.name))
        assert next(read_back) == list_to_write[0]
        assert int(next(read_back)) == list_to_write[1]