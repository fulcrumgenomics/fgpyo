from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

try:
    __version__ = version("fgpyo")
except PackageNotFoundError:
    __version__ = "dev"  # package is not installed
