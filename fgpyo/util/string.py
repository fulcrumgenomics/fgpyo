from typing import List


def column_it(rows: List[List[str]], delimiter: str = " ") -> str:
    """A simple version of Unix's `column` utility.  This assumes the table is NxM.

    Args:
        rows: the rows to adjust.  Each row must have the same number of delimited fields.
        delimiter: the delimiter for each field in a row.
    """
    # get the # of columns
    num_columns = len(rows[0])
    # for each column, find the maximum length of a cell
    max_column_lengths: List[int] = [
        max(len(row[col_i]) for row in rows) for col_i in range(num_columns)
    ]
    # pad each row in the table
    return "\n".join(
        delimiter.join(
            (" " * (max_column_lengths[col_i] - len(row[col_i]))) + row[col_i]
            for col_i in range(num_columns)
        )
        for row in rows
    )
