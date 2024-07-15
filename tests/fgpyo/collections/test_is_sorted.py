from functools import total_ordering
from typing import Any
from typing import List

import pytest

from fgpyo.collections import is_sorted


def test_is_sorted_empty_input() -> None:
    """Test is_sorted on a variety of empty collections."""
    assert is_sorted(tuple())
    assert is_sorted(list())
    assert is_sorted(iter([]))
    assert is_sorted(dict())


def test_is_sorted_on_single_element_collections() -> None:
    """Test is_sorted on collections with a single element."""
    assert is_sorted((1,))
    assert is_sorted([1])
    assert is_sorted(iter([1]))
    assert is_sorted({1: 1})


# NB: this 2-element test exists due to special handling for this case in "pairwise"
def test_is_sorted_on_correctly_sorted_two_element_collections() -> None:
    """Test is_sorted on collections with two correctly sorted elements."""
    # two identical elements one after the other
    assert is_sorted([1, 1])
    assert is_sorted((1, 1))
    assert is_sorted(iter([1, 1]))

    # two elements monotonically increasing
    assert is_sorted((1, 2))
    assert is_sorted([1, 2])
    assert is_sorted(iter([1, 2]))
    assert is_sorted({1: 1, 2: 2})


# NB: this 2-element test exists due to special handling for this case in "pairwise"
def test_is_sorted_on_incorrectly_sorted_two_element_collections() -> None:
    """Test is_sorted on collections with two incorrectly sorted elements."""
    assert not is_sorted((2, 1))
    assert not is_sorted([2, 1])
    assert not is_sorted(iter([2, 1]))
    assert not is_sorted({2: 2, 1: 1})


def test_is_sorted_on_correctly_sorted_collections_with_more_than_two_elements() -> None:
    """Test is_sorted on sorted collections with more than two elements."""
    # three identical elements one after the other
    assert is_sorted([1, 1, 1])
    assert is_sorted((1, 1, 1))
    assert is_sorted(iter([1, 1, 1]))

    # three elements monotonically increasing
    assert is_sorted((1, 2, 3))
    assert is_sorted([1, 2, 3])
    assert is_sorted(iter([1, 2, 3]))
    assert is_sorted({1: 1, 2: 2, 3: 3})


def test_is_sorted_on_incorrectly_sorted_collections_with_more_than_two_elements() -> None:
    """Test is_sorted on non-sorted collections with more than two elements."""
    assert not is_sorted((1, 3, 2))
    assert not is_sorted([1, 3, 2])
    assert not is_sorted(iter([1, 3, 2]))
    assert not is_sorted({1: 1, 3: 3, 2: 2})


def test_is_sorted_raises_on_non_comparable_objects() -> None:
    """Test is_sorted raises an exception on a collection containing non-comparable objects."""

    class MyClass:
        """A test class that is not comparable but does have a comparable field."""

        def __init__(self, field: int) -> None:
            self.field = field

    # NB: an exception is only raised when there are more than one objects
    iterable: List[MyClass] = [MyClass(field=1), MyClass(field=2)]

    with pytest.raises(TypeError):
        # NB: the type ignore below checks that MyPy is aware the custom class is incorrectly typed
        is_sorted(iterable)  # type: ignore[type-var]


def test_is_sorted_on_custom_comparable_objects() -> None:
    """Test is_sorted on a custom collection containing comparable objects."""

    @total_ordering
    class MyClass:
        """A test class that is comparable by relying on a comparable field."""

        def __init__(self, field: int) -> None:
            self.field = field

        def __eq__(self, other: Any) -> bool:
            if isinstance(other, type(self)):
                return self.field == other.field
            return NotImplemented

        def __le__(self, other: Any) -> bool:
            if isinstance(other, type(self)):
                return self.field <= other.field
            return NotImplemented

    # NB: comparisons only occur when there are more than one object in the iterable.
    iterable_sorted: List[MyClass] = [MyClass(field=1), MyClass(field=2)]
    iterable_unsorted: List[MyClass] = [MyClass(field=2), MyClass(field=1)]

    assert is_sorted(iterable_sorted)
    assert not is_sorted(iterable_unsorted)
