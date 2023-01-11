"""
I/O
-------
# TODO fix examples section/desciptions
Module for reading and writing

The :class:`~fgpyo.io.io.IO` class makes it easy to...

Examples
~~~~~~~~

Defining a new IO class:

.. code-block:: python

   >>> from fgpyo.io.io import IO
   >>> import attr
   >>> @attr.s(auto_attribs=True, frozen=True)
   # TODO 
   """

import gzip
import os
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional

import attr


# TODO ask Tim/Nils if I should only use pathlib or os
@attr.s(frozen=True, auto_attribs=True)
class IO:
    """
    Doc string place holder
    """

    paths: List[Path]
    extension: Optional[str] = None

    def _file_exists(self, path: Path) -> bool:
        """ Checks that file exists """
        if path.is_file():
            return True
        else:
            raise FileNotFoundError

    def _directory_exists(self, path: Path) -> bool:
        """ Checks that directory exists """
        if path.is_dir():
            return True
        else:
            raise NotADirectoryError

    def _readable(self, path: Path) -> bool:
        """ Checks path is readable """
        if os.access(path, os.R_OK):
            return True
        else:
            raise Exception(f"{path} is not readable")

    def _writeable(self, path: Path) -> bool:
        """ Checks that path is writable """
        if os.access(path, os.W_OK):
            return True
        else:
            raise Exception(f"{path} is not writeable")

    def paths_are_writeable(self) -> None:
        """Checks that each path is paths exist and are directories"""
        for path in self.paths:
            # Is path a directory or a path?
            if self._file_exists(path=path):
                path_is_file: bool = True
            elif self._directory_exists(path=path):
                path_is_file = False
            else:
                raise OSError(f"{path} is neither file or directory")

            if path_is_file:
                parent_dir = path.parent.absolute()
                if self._directory_exists(path=parent_dir):
                    # Check that directory is writeable
                    if self._writeable(parent_dir) and self._writeable(path=Path(path.name)):
                        print("It works!")
                    else:
                        raise Exception(f"{parent_dir} and or {path.name} are not writeable")

    def reader(self) -> Any:
        """Opens a Path for reading and based on extension uses open() or gzip.open()"""
        special_suffix: set[str] = {".gz", ".bgz"}
        for path in self.paths:
            if path.suffix in special_suffix:
                return gzip.open(path, "r")
            else:
                return path.open("r")

    def writer(self) -> Any:
        """Opens a Path for reading and based on extension uses open() or gzip.open()"""
        special_suffix: set[str] = {".gz", ".bgz"}
        for path in self.paths:
            if path.suffix in special_suffix:
                return gzip.open(path, "w")
            else:
                return path.open("w")


# def reader(self) -> None:


# example = IO([Path("dummy.txt")])
# example.paths_are_writeable()
