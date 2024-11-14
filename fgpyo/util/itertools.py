import heapq
from dataclasses import dataclass
from dataclasses import field
from typing import Callable
from typing import Collection
from typing import Generic
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import TypeVar

T = TypeVar("T")


@dataclass(order=True)
class Coord:
    x: int
    y: int

    def incr_x(self) -> "Coord":
        return Coord(self.x + 1, self.y)

    def incr_y(self) -> "Coord":
        return Coord(self.x, self.y + 1)


@dataclass(order=True)
class HeapElem(Generic[T]):
    _priority: float
    val: Tuple[T, T] = field(compare=False)
    coord: Coord  # NB: sorting must also be stable / deterministic on the coordinates

    @classmethod
    def new(cls, x: T, y: T, coord: Coord, priority: Callable[[T], float]) -> "HeapElem":
        return cls(_priority=priority(x) + priority(y), val=(x, y), coord=coord)


class ProductSumTable(Generic[T]):
    xs: List[T]
    ys: List[T]
    priority: Callable[[T], float]

    def __init__(self, xs: Iterable[T], ys: Iterable[T], priority: Callable[[T], float]) -> None:
        self.xs = list(xs)
        self.ys = list(ys)
        self.priority = priority

    def has_right(self, elem: HeapElem) -> bool:
        return (elem.coord.x + 1) < len(self.xs)

    def has_down(self, elem: HeapElem) -> bool:
        return (elem.coord.y + 1) < len(self.ys)

    def is_last(self, elem: HeapElem) -> bool:
        return (elem.coord.y + 1) == len(self.ys) and (elem.coord.x + 1) == len(self.xs)

    def get_elem(self, coord: Coord) -> HeapElem:
        x: T = self.xs[coord.x]
        y: T = self.ys[coord.y]

        return HeapElem.new(x=x, y=y, coord=coord, priority=self.priority)

    def get_right(self, elem: HeapElem) -> HeapElem:
        assert self.has_right(elem)
        coord = elem.coord.incr_x()
        return self.get_elem(coord)

    def get_down(self, elem: HeapElem) -> HeapElem:
        assert self.has_down(elem)
        coord = elem.coord.incr_y()
        return self.get_elem(coord)

    def get_last(self) -> HeapElem:
        x: T = self.xs[-1]
        y: T = self.ys[-1]

        return HeapElem.new(
            x=x, y=y, coord=Coord(len(self.xs) - 1, len(self.ys) - 1), priority=self.priority
        )


def sorted_product(
    xs: Collection[T],
    ys: Collection[T],
    priority: Callable[[T], float],
    limit: Optional[int] = None,
) -> List[Tuple[T, T]]:
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

    table: ProductSumTable = ProductSumTable(xs=xs, ys=ys, priority=priority)
    curr: HeapElem[T] = table.get_elem(Coord(x=0, y=0))

    # Each heap element corresponds to a single pairing in the product.
    # `heap` contains the current heap, and `result` contains the sorted pairings generated so far.
    heap: List[HeapElem[T]] = []
    result: List[HeapElem[T]] = []

    # If no limit is specified, generate all elements.
    if limit is None:
        limit = len(xs) * len(ys)

    # TODO: yield instead of generating `results` list
    while not table.is_last(curr) and len(result) < limit:
        result.append(curr)
        if len(heap) > 0:
            if heap[0].coord == curr.coord:
                heapq.heappop(heap)

        if len(heap) > 0:
            top = heap[0]
            if not table.has_right(curr) and table.has_down(curr):
                down = table.get_down(curr)
                if down < top:
                    curr = down
                else:
                    curr = heapq.heappushpop(heap, down)
            elif table.has_right(curr) and not table.has_down(curr):
                right = table.get_right(curr)
                if right <= top:
                    curr = right
                else:
                    curr = heapq.heappushpop(heap, right)
            else:
                down = table.get_down(curr)
                right = table.get_right(curr)

                if right <= down and right <= top:
                    curr = right
                    heapq.heappush(heap, down)
                elif down <= right and down <= top:
                    curr = down
                    heapq.heappush(heap, right)
                else:
                    curr = heapq.heappushpop(heap, down)
                    heapq.heappush(heap, right)
        else:
            if not table.has_right(curr) and table.has_down(curr):
                curr = table.get_down(curr)
            elif table.has_right(curr) and not table.has_down(curr):
                curr = table.get_right(curr)
            else:
                right = table.get_right(curr)
                down = table.get_down(curr)
                if right <= down:
                    heapq.heappush(heap, down)
                    curr = right
                else:
                    heapq.heappush(heap, right)
                    curr = down

    result.append(curr)

    if len(heap) > 0 and heap[0].coord != curr.coord:
        result.append(heap[0])

    return [elem.val for elem in result]
