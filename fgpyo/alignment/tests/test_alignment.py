import pytest

from fgpyo.alignment import Alignment
from fgpyo.sam import Cigar


def test_padded_string_simple_alignment() -> None:
    expected = [
        "AACCGGTT",
        "||||||||",
        "AACCGGTT",
    ]
    alignment = Alignment(
        expected[0].replace("-", ""),
        expected[-1].replace("-", ""),
        1,
        1,
        Cigar.from_cigarstring("8M"),
        1,
    )
    assert alignment.padded_string() == expected


def test_padded_string_single_mismatch() -> None:
    expected = [
        "AACCGGTT",
        "||||||.|",
        "AACCGGGT",
    ]
    cigar_strings = ["8M", "6=1X1="]
    for cigar in cigar_strings:
        alignment = Alignment(
            expected[0].replace("-", ""),
            expected[-1].replace("-", ""),
            1,
            1,
            Cigar.from_cigarstring(cigar),
            1,
        )
        assert alignment.padded_string() == expected


def test_padded_string_with_insertions_and_deletions() -> None:
    expected = [
        "AA--GGGTAAACC-GGGTTT",
        "||  ||||||||| || |||",
        "AACCGGGTAAACCCGG-TTT",
    ]
    alignment = Alignment(
        expected[0].replace("-", ""),
        expected[-1].replace("-", ""),
        1,
        1,
        Cigar.from_cigarstring("2=2D9=1D2=1I3="),
        1,
    )
    assert alignment.padded_string() == expected


def test_padded_string_messy_alignment() -> None:
    expected = [
        "AA--GGGGGAACC-GGGTTT",
        "||  |||..|||| || |||",
        "AACCGGGTAAACCCGG-TTT",
    ]
    alignment = Alignment(
        expected[0].replace("-", ""),
        expected[-1].replace("-", ""),
        1,
        1,
        Cigar.from_cigarstring("2M2D9M1D2M1I3M"),
        1,
    )
    assert alignment.padded_string() == expected


@pytest.mark.parametrize("cigar", ["5S10M", "10M5H", "5M50N5M", "50P10M"])
def test_padded_string_exception_with_unsupported_operator(cigar: str) -> None:
    cig = Cigar.from_cigarstring(cigar)
    alignment = Alignment("AAAAAAAAAA", "AAAAAAAAAA", 1, 1, cig, 1)
    with pytest.raises(Exception):
        alignment.padded_string()


def test_padded_string_with_alternative_characters() -> None:
    expected = [
        "AA..GGGGGAACC.GGGTTT",
        "++--+++##++++-++-+++",
        "AACCGGGTAAACCCGG.TTT",
    ]
    alignment = Alignment(
        expected[0].replace(".", ""),
        expected[-1].replace(".", ""),
        1,
        1,
        Cigar.from_cigarstring("2M2D9M1D2M1I3M"),
        1,
    )
    assert (
        alignment.padded_string(match_char="+", mismatch_char="#", gap_char="-", pad_char=".")
        == expected
    )


def test_sub_by_target_all_bases_aligned() -> None:
    sub = Alignment(
        "AAAAAAAAAA", "AAAAAAAAAA", 1, 1, Cigar.from_cigarstring("10M"), 10
    ).sub_by_target(5, 6)
    assert sub.target_start == 5
    assert sub.query_start == 5
    assert sub.cigar.__str__() == "2M"


def test_sub_by_target_remove_cigar_elements_outside_sub_region() -> None:
    sub = Alignment(
        "AAAAAAAAAA", "ATAAAAAATA", 1, 1, Cigar.from_cigarstring("1=1X6=1X1="), 10
    ).sub_by_target(5, 6)
    assert sub.target_start == 5
    assert sub.query_start == 5
    assert sub.cigar.__str__() == "2="


def test_sub_by_target_alignment_start_end_not_1() -> None:
    sub = Alignment(
        "AAAAAAAAAA", "ATAAAAAATA", 3, 3, Cigar.from_cigarstring("6="), 6
    ).sub_by_target(5, 6)
    assert sub.target_start == 5
    assert sub.query_start == 5
    assert sub.cigar.__str__() == "2="


def test_sub_by_target_insertions() -> None:
    sub = Alignment(
        "AAAAATTAAAAA", "AAAAAAAAAA", 1, 1, Cigar.from_cigarstring("5=2I5="), 10
    ).sub_by_target(3, 8)
    assert sub.target_start == 3
    assert sub.query_start == 3
    assert sub.cigar.__str__() == "3=2I3="


def test_sub_by_target_deletions() -> None:
    sub = Alignment(
        "AAAAAAAAAA", "AAAAATTAAAAA", 1, 1, Cigar.from_cigarstring("5=2D5="), 10
    ).sub_by_target(3, 8)
    assert sub.target_start == 3
    assert sub.query_start == 3
    assert sub.cigar.__str__() == "3=2D1="


def test_sub_by_target_drop_adjacent_insertions_deletions() -> None:
    sub = Alignment(
        "AACCAAAAAAAA", "AAAAAAAATTAA", 1, 1, Cigar.from_cigarstring("2=2I6=2D2="), 10
    ).sub_by_target(3, 8)
    assert sub.target_start == 3
    assert sub.query_start == 5
    assert sub.cigar.__str__() == "6="


def test_sub_by_target_fail_start_end_outside_alignment() -> None:
    with pytest.raises(Exception):
        Alignment("AAAAA", "TAAAT", 2, 2, Cigar.from_cigarstring("3="), 0).sub_by_target(1, 3)
    with pytest.raises(Exception):
        Alignment("AAAAA", "TAAAT", 2, 2, Cigar.from_cigarstring("3="), 0).sub_by_target(2, 5)


def test_handle_real_world_test_case() -> None:
    query = "GGCCAGAGTCCACAGATTAACCAGGGGATATGCTAGAAA"
    target = "CAGAGGCCACAGATTAACCAGGGGATATGCTAGAAA"
    ali = Alignment(query, target, 1, 1, Cigar.from_cigarstring("3I5=1X30="), 0)
    sub = ali.sub_by_target(1, 20)
    assert sub.query_start == 4
    assert sub.target_start == 1
    assert sub.cigar.__str__() == "5=1X14="


def test_sub_by_query_all_bases_aligned() -> None:
    sub = Alignment(
        "AAAAAAAAAA", "AAAAAAAAAA", 1, 1, Cigar.from_cigarstring("10M"), 10
    ).sub_by_query(5, 6)
    assert sub.target_start == 5
    assert sub.query_start == 5
    assert sub.cigar.__str__() == "2M"


def test_sub_by_query_start_end_outside_alignment() -> None:
    with pytest.raises(Exception):
        Alignment("TCGAAAAGGA", "AAAA", 4, 1, Cigar.from_cigarstring("4="), 0).sub_by_query(1, 6)
    with pytest.raises(Exception):
        Alignment("TCGAAAAGGA", "AAAA", 4, 1, Cigar.from_cigarstring("4="), 0).sub_by_query(5, 9)


def test_sub_by_query_deletions_1bp_away_from_end() -> None:
    alignment = Alignment(
        "AAAAAAAAAA", "AAAAATTTTTAAAAA", 1, 1, Cigar.from_cigarstring("5=5D5="), 0
    )
    assert alignment.sub_by_query(1, 5).cigar.__str__() == "5="
    assert alignment.sub_by_query(1, 6).cigar.__str__() == "5=5D1="
    assert alignment.sub_by_query(5, 10).cigar.__str__() == "1=5D5="
    assert alignment.sub_by_query(6, 10).cigar.__str__() == "5="

    assert alignment.sub_by_target(1, 5).cigar.__str__() == "5="
    assert alignment.sub_by_target(1, 6).cigar.__str__() == "5=1D"
    assert alignment.sub_by_target(5, 10).cigar.__str__() == "1=5D"
    assert alignment.sub_by_target(6, 11).cigar.__str__() == "5D1="
    assert alignment.sub_by_target(5, 10).cigar.__str__() == "1=5D"
    assert alignment.sub_by_target(5, 11).cigar.__str__() == "1=5D1="
    assert alignment.sub_by_target(6, 10).cigar.__str__() == "5D"
    assert alignment.sub_by_target(6, 11).cigar.__str__() == "5D1="
