from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from fgpyo._requirements import RequirementError
from fgpyo._requirements import fail
from fgpyo._requirements import require
from fgpyo._requirements import require_not_none

try:
    __version__ = version("fgpyo")
except PackageNotFoundError:
    __version__ = "dev"  # package is not installed

__all__ = [
    "RequirementError",
    "fail",
    "require",
    "require_not_none",
]
