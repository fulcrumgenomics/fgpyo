from dataclasses import dataclass

import pytest

from fgpyo.collections import DataSubclassMixin


@dataclass
class MyData:
    foo: str
    bar: int


@dataclass
class OtherData:
    x: str
    y: int


@dataclass
class MySubData(MyData, DataSubclassMixin):
    baz: float


def test_from_parent() -> None:
    """Test we can construct a subclass instance from a parent instance."""
    data = MyData(foo="hello", bar=42)

    assert MySubData.from_parent(data, baz=0.0) == MySubData(foo="hello", bar=42, baz=0.0)


def test_datasubclass_mixin_fails() -> None:
    """`from_parent` should fail when the parent is not a superclass of the dataclass."""
    data = OtherData(x="bad", y=3)

    with pytest.raises(TypeError):
        MySubData.from_parent(data, baz=0.0)
