"""Basic tests for io module"""

import io
import os
import stat
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from typing import List

import pytest

import fgpyo.io as fio
from fgpyo.io import assert_path_is_writable
from fgpyo.io import assert_path_is_writeable


def test_assert_path_is_readable_missing_file_error() -> None:
    """Error when file does not exist"""
    path = Path("error.txt")

    with pytest.raises(AssertionError):
        fio.assert_path_is_readable(path=path)


def test_assert_path_is_readable_mode_error() -> None:
    """Error when permissions are write only by owner"""
    with NamedTemporaryFile(suffix=".txt", mode="r", delete=True) as write_file:
        path = Path(write_file.name)
        os.chmod(path, stat.S_IWUSR)  # Write only permissions

        with pytest.raises(AssertionError):
            fio.assert_path_is_readable(path=path)


def test_assert_path_is_readable_pass() -> None:
    """Returns none when no assertions are violated"""
    with NamedTemporaryFile(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        fio.assert_path_is_readable(path=path)


def test_assert_directory_exists_error() -> None:
    """Ensure OSError when directory does not exist"""
    path = Path("/non/existent/dir/")
    with pytest.raises(AssertionError):
        fio.assert_directory_exists(path)


def test_assert_directory_exists_pass() -> None:
    """Asserts fio._assert_directory_exists() returns True when directory exists"""
    with NamedTemporaryFile(suffix=".txt", mode="w", delete=True) as write_file:
        path = Path(write_file.name)
        fio.assert_directory_exists(path=path.parent.absolute())


def test_assert_path_is_writable_mode_error() -> None:
    """Error when permissions are read only by owner"""
    with NamedTemporaryFile(suffix=".txt", mode="w", delete=True) as read_file:
        path = Path(read_file.name)
        os.chmod(path, stat.S_IRUSR)  # Read only permissions
        with pytest.raises(AssertionError, match=f"File exists but is not writable: {path}"):
            assert_path_is_writable(path=path)


def test_assert_path_is_writable_parent_not_writable() -> None:
    """Error when parent_must_exist is false and no writable parent directory exists"""
    path = Path("/no/parent/exists/")
    with pytest.raises(AssertionError, match="Parent directory is not writable: /"):
        assert_path_is_writable(path=path, parent_must_exist=False)


def test_assert_path_is_writable_file_does_not_exist() -> None:
    """Error when file does not exist"""
    path = Path("example/non_existent_file.txt")
    with pytest.raises(AssertionError, match="Parent directory does not exist:"):
        assert_path_is_writable(path=path)


def test_assert_path_is_writable_pass() -> None:
    """Should return the correct writable path"""
    with NamedTemporaryFile(suffix=".txt", mode="w", delete=True) as read_file:
        path = Path(read_file.name)
        assert_path_is_writable(path=path)


def test_assert_path_is_writeable_raises_deprecation_warning(tmp_path: Path) -> None:
    """
    Test that we get a DeprecationWarning when the `assert_path_is_writeable` alias is called,
    but otherwise works as expected.
    """
    with pytest.warns(DeprecationWarning):
        assert_path_is_writeable(path=tmp_path / "test.txt")


@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".gz", io.TextIOWrapper),
        (".fa", io.TextIOWrapper),
    ],
)
def test_reader(
    suffix: str,
    expected: Any,
) -> None:
    """Tests fgpyo.io.to_reader"""
    with NamedTemporaryFile(suffix=suffix, mode="r", delete=True) as read_file:
        with fio.to_reader(path=Path(read_file.name)) as reader:
            assert isinstance(reader, expected)


@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".gz", io.TextIOWrapper),
        (".fa", io.TextIOWrapper),
    ],
)
def test_writer(
    suffix: str,
    expected: Any,
) -> None:
    """Tests fgpyo.io.to_writer()"""
    with NamedTemporaryFile(suffix=suffix, mode="w", delete=True) as write_file:
        with fio.to_writer(path=Path(write_file.name)) as writer:
            assert isinstance(writer, expected)


@pytest.mark.parametrize(
    "suffix, list_to_write",
    [(".txt", ["Test with a flat file", 10]), (".gz", ["Test with a gzip file", 10])],
)
def test_read_and_write_lines(
    suffix: str,
    list_to_write: List[Any],
) -> None:
    """Test fgpyo.fio.read_lines and write_lines"""
    with NamedTemporaryFile(suffix=suffix, mode="w", delete=True) as read_file:
        fio.write_lines(path=Path(read_file.name), lines_to_write=list_to_write)
        read_back = fio.read_lines(path=Path(read_file.name))
        assert next(read_back) == list_to_write[0]
        assert int(next(read_back)) == list_to_write[1]
