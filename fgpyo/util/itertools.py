from dataclasses import dataclass
from typing import TypeVar, Callable, Iterable, Iterator

T = TypeVar('T')


def sorted_product(
    xs: Iterable[T],
    ys: Iterable[T],
    priority: Callable[[T], float],
    limit: int | None = None,
) -> Iterator[tuple[T, T]]:
    """
    Efficient generation of the sorted Cartesian product of two sorted lists.

    Args:
        xs: A sorted list of elements.
        ys: A sorted list of elements.
        priority: A function that assigns a priority to each element.
        limit: If specified, only the first `limit` elements of the product will be generated.

    Yields:
        Each tuple (x, y) from the Cartesian product of xs and ys, sorted by the sum of the priority
        of x and y.
    """
