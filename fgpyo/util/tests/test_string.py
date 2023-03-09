import pytest

from fgpyo.util.string import column_it


def test_columnit_unequal_number_of_columns() -> None:
    with pytest.raises(IndexError):
        column_it(rows=[["1,1", "1,2"], ["2,1"]])


def test_columnit_ok() -> None:
    assert column_it(rows=[["1,1", "1,2"], ["2,1", "2,2"]]) == "1,1 1,2\n2,1 2,2"
    assert column_it(rows=[["1,1", "1,2"], ["2,1", "2,2"]], delimiter="|") == "1,1|1,2\n2,1|2,2"
    assert column_it(rows=[["1,1", "1,2x"], ["2,1", "2,2"]]) == "1,1 1,2x\n2,1  2,2"
    assert column_it(rows=[["1,1x", "1,2"], ["2,1", "2,2"]]) == "1,1x 1,2\n 2,1 2,2"
