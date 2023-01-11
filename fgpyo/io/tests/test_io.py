"""Basic tests for io module"""

import gzip
import io
import os
from pathlib import Path
from tempfile import NamedTemporaryFile as NamedTemp
from typing import Any

import pytest
from pytest import raises

from fgpyo.io.io import IO


def test_file_exists_error() -> None:
    """Ensure FileNotFoundError"""
    path = Path("error.txt")
    test_io = IO([path])
    with raises(FileNotFoundError):
        test_io._file_exists(path)


def test_dir_exists_error() -> None:
    """Ensure OSError when directory does not exist"""
    path = Path("/non/existant/dir/")
    test_io = IO([path])
    with raises(NotADirectoryError):
        test_io._directory_exists(path)


def test_readable_rrror() -> None:
    """Error when permissions are write only by owner"""
    with NamedTemp(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        test_io = IO([path])
        os.chmod(path, 0o00200)  # Write only permissions
        with raises(Exception):
            test_io._readable(path=path)


def test_writeable_error() -> None:
    """Error when permissions are read only by owner"""
    with NamedTemp(suffix=".txt", mode="r", delete=True) as read_file:
        path = Path(read_file.name)
        test_io = IO([path])
        os.chmod(path, 0o00400)  # Read only permissions
        with raises(Exception):
            test_io._writable(path=path)


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
    """Tests reader"""
    with NamedTemp(suffix=suffix, mode="r", delete=True) as read_file:
        test_io = IO([Path(read_file.name)])
        file = test_io.reader()
        assert isinstance(file, expected)
        file.close()
