"""
Functions for Working with Collections
--------------------------------------

This module contains classes and functions for working with collections and iterators.

Examples of a "Peekable" Iterator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"Peekable" iterators are useful to "peek" at the next item in an iterator without consuming it.
For example, this is useful when consuming items in iterator while a predicate is true, and not
consuming the first element where the element is not true.  See the
:func:`~fgpyo.collections.PeekableIterator.takewhile` and
:func:`~fgpyo.collections.PeekableIterator.dropwhile` methods.

An empty peekable iterator throws StopIteration:

.. code-block:: python

    >>> from fgpyo.collections import PeekableIterator
    >>> piter = PeekableIterator(iter([]))
    >>> piter.peek()
    StopIteration

A peekable iterator will return the next item before consuming it.

.. code-block:: python

    >>> piter = PeekableIterator([1, 2, 3])
    >>> piter.peek()
    1
    >>> next(piter)
    1
    >>> [j for j in piter]
    [2, 3]

The `can_peek()` function can be used to determine if the iterator can be peeked without
StopIteration being thrown:

    >>> piter = PeekableIterator([1])
    >>> piter.peek() if piter.can_peek() else -1
    1
    >>> next(piter)
    1
    >>> piter.peek() if piter.can_peek() else -1
    -1
    >>> next(piter)
    StopIteration

`PeekableIterator`'s constructor supports creation from iterable objects as well as iterators.

Module Contents
~~~~~~~~~~~~~~~

The module contains the following public classes:

    - :class:`~fgpyo.collections.PeekableIterator` -- Iterator that allows you to peek at the
        next value before calling next

"""

from typing import Any
from typing import Callable
from typing import Generic
from typing import Iterable
from typing import Iterator
from typing import List
from typing import TypeVar
from typing import Union

IterType = TypeVar("IterType")


class PeekableIterator(Generic[IterType], Iterator[IterType]):
    """A peekable iterator wrapping an iterator or iterable.

    This allows returning the next item without consuming it.

    Args:
        source: an iterator over the objects
    """

    def __init__(self, source: Union[Iterator[IterType], Iterable[IterType]]) -> None:
        self._iter: Iterator[IterType] = iter(source)
        self._sentinel: Any = object()
        self.__update_peek()

    def __iter__(self) -> Iterator[IterType]:
        return self

    def __next__(self) -> IterType:
        to_return = self.peek()
        self.__update_peek()
        return to_return

    def __update_peek(self) -> None:
        self._peek = next(self._iter, self._sentinel)

    def can_peek(self) -> bool:
        """Returns true if there is a value that can be peeked at, false otherwise."""
        return self._peek is not self._sentinel

    def peek(self) -> IterType:
        """Returns the next element without consuming it, or StopIteration otherwise."""
        if self.can_peek():
            return self._peek
        else:
            raise StopIteration

    def takewhile(self, pred: Callable[[IterType], bool]) -> List[IterType]:
        """Consumes from the iterator while pred is true, and returns the result as a List.

        The iterator is left pointing at the first non-matching item, or if all items match
        then the iterator will be exhausted.

        Args:
            pred: a function that takes the next value from the iterator and returns
                  true or false.

        Returns:
            List[V]: A list of the values from the iterator, in order, up until and excluding
            the first value that does not match the predicate.
        """
        xs: List[IterType] = []
        while self.can_peek() and pred(self._peek):
            xs.append(next(self))
        return xs

    def dropwhile(self, pred: Callable[[IterType], bool]) -> "PeekableIterator[IterType]":
        """Drops elements from the iterator while the predicate is true.

        Updates the iterator to point at the first non-matching element, or exhausts the
        iterator if all elements match the predicate.

        Args:
            pred (Callable[[V], bool]): a function that takes a value from the iterator
            and returns true or false.

        Returns:
            PeekableIterator[V]: a reference to this iterator, so calls can be chained
        """
        while self.can_peek() and pred(self._peek):
            self.__update_peek()
        return self
