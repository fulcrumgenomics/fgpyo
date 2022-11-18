"""Tests for :py:mod:`~fgpyo.collections.PeekableIterator`"""

import pytest

from fgpyo.collections import PeekableIterator


def test_peekable_iterator_empty() -> None:
    empty_iter: PeekableIterator[None] = PeekableIterator([])
    assert not empty_iter.can_peek()
    with pytest.raises(StopIteration):
        empty_iter.peek()
    with pytest.raises(StopIteration):
        next(empty_iter)


def test_peekable_iterator_nonempty() -> None:
    nonempty_iter = PeekableIterator(range(10))
    for i in range(10):
        assert nonempty_iter.can_peek()
        assert nonempty_iter.peek() == i
        assert next(nonempty_iter) == i

    with pytest.raises(StopIteration):
        nonempty_iter.peek()
    with pytest.raises(StopIteration):
        next(nonempty_iter)


def test_peekable_with_nones() -> None:
    xs = [1, 2, None, 4, None, 6]
    iterator = PeekableIterator(xs)

    for i in range(len(xs)):
        assert iterator.peek() is xs[i]
        assert next(iterator) is xs[i]


def test_takewhile() -> None:
    xs = [2, 4, 6, 8, 11, 13, 15, 17, 19, 20, 22, 24]
    iterator = PeekableIterator(xs)
    assert iterator.takewhile(lambda x: x % 2 == 0) == [2, 4, 6, 8]
    assert iterator.takewhile(lambda x: x % 2 == 1) == [11, 13, 15, 17, 19]
    assert iterator.takewhile(lambda x: x % 2 == 1) == []
    assert iterator.takewhile(lambda x: x % 2 == 0) == [20, 22, 24]


def test_dropwhile() -> None:
    xs = [2, 4, 6, 8, 11, 13, 15, 17, 19, 20, 22, 24]
    iterator = PeekableIterator(xs)
    iterator.dropwhile(lambda x: x % 2 == 0)
    iterator.dropwhile(lambda x: x <= 20)
    assert list(iterator) == [22, 24]
