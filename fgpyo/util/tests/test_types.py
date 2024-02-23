from typing import Iterable
from typing import List
from typing import Sequence

from fgpyo.util import types


def test_is_listlike() -> None:
    assert types.is_list_like(List[str])
    assert types.is_list_like(Iterable[str])
    assert types.is_list_like(Sequence[str])
