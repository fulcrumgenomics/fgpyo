import sys
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union

import pytest

from fgpyo.util import types
from fgpyo.util.inspect import NoneType


def test_is_listlike() -> None:
    assert types.is_list_like(List[str])
    assert types.is_list_like(Iterable[str])
    assert types.is_list_like(Sequence[str])
    assert not types.is_list_like(str)


@pytest.mark.parametrize(
    "tpe, expected",
    [
        (Union[str, NoneType], True),
        (Optional[str], True),
        (Union[str, int], False),
        (Union[str, int, None], False),
        (str, False),
    ],
)
def test_is_optional(tpe: Type, expected: bool) -> None:
    assert types._is_optional(tpe) == expected


def test_is_optional_wrong_type() -> None:
    with pytest.raises(TypeError, match="Expected type annotation"):
        types._is_optional(None)


if sys.version_info >= (3, 10):

    def test_is_optional_python_310() -> None:
        assert types._is_optional(str | None)

    def test_make_union_parser_worker_exception() -> None:
        class Foo:
            pass

        class Bar:
            pass

        with pytest.raises(ValueError, match="foo could not be parsed"):
            type_ = type((Foo | Bar))
            types._make_union_parser_worker(union=type_, parsers=[], value="foo")
            pass

