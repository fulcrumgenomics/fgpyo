from itertools import product
from typing import List
from typing import Tuple

from typing_extensions import TypeAlias

from fgpyo.util.itertools import sorted_product


def test_sorted_product() -> None:
    """sorted_product should return a sorted cartesian product of the input lists."""
    xs: List[int] = [25, 10, 10, 1]
    ys: List[int] = [1, 2, 10]

    Pairing: TypeAlias = Tuple[int, int]
    actual_product: List[Pairing] = list(sorted_product(xs, ys, priority=lambda x: float(x)))

    # We should get the same result as using `itertools.product` and then sorting, the
    # implementation is just more efficient (in most cases).
    expected_product: List[Pairing] = sorted(product(xs, ys), key=lambda tup: tup[0] + tup[1], reverse=True)

    assert actual_product == expected_product
