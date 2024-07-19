import sys
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Union

from fgpyo.util import types
from fgpyo.util.inspect import NoneType


def test_is_listlike() -> None:
    assert types.is_list_like(List[str])
    assert types.is_list_like(Iterable[str])
    assert types.is_list_like(Sequence[str])
    assert not types.is_list_like(str)


def test_is_optional() -> None:
    assert types._is_optional(Union[str, NoneType])
    assert types._is_optional(Optional[str])
    assert not types._is_optional(str)


if sys.version_info >= (3, 10):

    def test_is_optional_python_310() -> None:
        assert types._is_optional(str | None)
