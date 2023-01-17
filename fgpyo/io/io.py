# TODO make more like scala version
"""
I/O
-------
Module for reading and writing files.

# TODO add details
The :class:`~fgpyo.io.io.IO` class makes it easy to...

Examples
~~~~~~~~

Examples:
.. code-block:: bash
   >>> echo 'example\nfile' > example.txt
   >>> cp example.txt example_gzip.txt
   >>> gzip example_gzip.txt
.. code-block:: python
   >>> from fgpyo.io.io import IO
   >>> from pathlib import Path
   >>> io = IO([Path("example.txt"), Path(("example_gzip.txt.gz"))])
   Assert that paths exist and are readable
   >>> io.paths_are_readable()
   Assert that paths exist and are writeable
   >>> io.paths_are_writeable()
   Read lines from paths into a list of strings
   >>> io.read_lines(path = Path("example.txt"))
   ['example', 'file']
   >>> io.read_lines(path = Path("example_gzip.txt.gz"))
   ['example', 'file']
"""

import gzip
import io
import os
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional
from typing import Set

import attr


@attr.s(frozen=True, auto_attribs=True)
class IO:
    """
    Doc string place holder
    """

    paths: List[Path]
    extension: Optional[str] = None

    def _file_exists(self, path: Path) -> bool:
        """ Checks that file exists, else raises FileNotFOundError """
        if path.is_file():
            return True
        else:
            raise FileNotFoundError

    def _directory_exists(self, path: Path) -> bool:
        """ Checks that directory exists, else raises NotADirectoryError """
        if path.is_dir():
            return True
        else:
            raise NotADirectoryError

    def _readable(self, path: Path) -> bool:
        """ Checks path is readable, else raises an Exception """
        if os.access(path, os.R_OK):
            return True
        else:
            raise Exception(f"{path} is not readable")

    def _writeable(self, path: Path) -> bool:
        """ Checks that path is writable, else raises an Exception """
        if os.access(path, os.W_OK):
            return True
        else:
            raise Exception(f"{path} is not writeable")

    def paths_are_readable(self) -> None:
        """ Asserts that one or more Paths exist and are readable """
        for path in self.paths:
            # Assert path exists and is readable
            assert path.exists and self._readable(path=path)

    def paths_are_directories(self, path: Path) -> bool:
        """ Asserts that one or more Paths exist and are directories """
        try:
            # Assert path exists and is a directory
            assert path.exists and self._directory_exists(path=path)
            return True
        except FileNotFoundError or NotADirectoryError:
            return False

    def paths_are_writeable(self) -> None:
        """Asserts that one or more Paths pass the following criteria:
        1) Parent exists and is writeable
        2) File exists and is writeable
        OR
        3) File does not exist
        """
        # List of Paths:
        for path in self.paths:
            # Assert Path is a file and exists
            try:
                assert self._file_exists(path=path)
            except FileNotFoundError as error:
                (f"{error}: The provided path {self.paths} is not a file or does not exist")

            # Assert parent exists and is writeable
            try:
                assert self.paths_are_directories(path=path.parent.absolute()) and self._writeable(
                    path=path.parent.absolute()
                )
            except Exception:
                raise Exception(f"{path.parent.absolute()} does not exist and or is not writeable")

            # Finally assert that file is writeabe
            try:
                assert self._writeable(path=path)
            except Exception:
                raise Exception(f"{path.name} is not writeable")

    @staticmethod
    def reader(path: Path) -> io.IOBase:
        """Opens a Path for reading and based on extension uses open() or gzip.open()"""
        special_suffix: Set[str] = {".gz", ".bgz"}
        if path.suffix in special_suffix:
            # with gzip.open(path, mode="rt") as gzip_reader:
            # return gzip_reader
            return gzip.open(path, "r")
        else:
            return path.open("rt")

    @staticmethod
    def writer(path: Path) -> io.IOBase:
        """Opens a Path for reading and based on extension uses open() or gzip.open()"""
        special_suffix: Set[str] = {".gz", ".bgz"}
        if path.suffix in special_suffix:
            return gzip.open(path, "w")
        else:
            return path.open("w")

    def read_lines(self, path: Path) -> Any:
        """Takes a path and reads it into a list of strings, removing line terminators
        along the way. # TODO = With an option to strip lines"""
        special_suffix: Set[str] = {".gz", ".bgz"}
        # TODO ask Tim/Nils about best practice to protect memory with large file
        if path.suffix in special_suffix:
            with gzip.open(path, mode="rt") as gzip_input:
                list_of_lines = gzip_input.readlines()
                return [line.rstrip() for line in list_of_lines]

        else:
            with open(file=path, mode="r") as input_file:
                list_of_lines = input_file.readlines()
                return [line.rstrip() for line in list_of_lines]


# cl = IO([Path("example.txt.gz"), Path(("example2.txt"))])
# cl.paths_are_readable()
# cl = IO([Path("example2.txt")])
# x = cl.read_lines(path=Path("example.txt.gz"))
# x = cl.read_lines(path=Path("example2.txt"))
# print(x)
# y = IO.reader(path = Path("example.txt.gz"))
