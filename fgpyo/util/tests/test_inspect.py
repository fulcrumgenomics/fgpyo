from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import attr
import pytest

from fgpyo.util.inspect import attr_from
from fgpyo.util.inspect import attribute_has_default
from fgpyo.util.inspect import attribute_is_optional
from fgpyo.util.inspect import dict_parser
from fgpyo.util.inspect import list_parser
from fgpyo.util.inspect import set_parser
from fgpyo.util.inspect import tuple_parser


@attr.s(auto_attribs=True, frozen=True)
class Name:
    required: str
    custom_parser: str
    optional_no_default: Optional[str]
    optional_with_default_none: Optional[str] = None
    optional_with_default_some: Optional[str] = "foo"


def test_attr_from() -> None:
    name = attr_from(
        cls=Name,
        kwargs={"required": "required", "custom_parser": "before"},
        parsers={str: lambda value: "after" if value == "before" else value},
    )
    assert name.required == "required"
    assert name.custom_parser == "after"
    assert name.optional_no_default is None
    assert name.optional_with_default_none is None
    assert name.optional_with_default_some == "foo"


def test_attribute_is_optional() -> None:
    fields_dict = attr.fields_dict(Name)
    assert not attribute_is_optional(fields_dict["required"])
    assert not attribute_is_optional(fields_dict["custom_parser"])
    assert attribute_is_optional(fields_dict["optional_no_default"])
    assert attribute_is_optional(fields_dict["optional_with_default_none"])
    assert attribute_is_optional(fields_dict["optional_with_default_some"])


def test_attribute_has_default() -> None:
    fields_dict = attr.fields_dict(Name)
    assert not attribute_has_default(fields_dict["required"])
    assert not attribute_has_default(fields_dict["custom_parser"])
    assert attribute_has_default(fields_dict["optional_no_default"])
    assert attribute_has_default(fields_dict["optional_with_default_none"])
    assert attribute_has_default(fields_dict["optional_with_default_some"])


class Foo:
    pass


@attr.s(auto_attribs=True, frozen=True)
class Bar:
    foo: Foo


# Test for regression #94 - the call to attr_from succeeds when the check for None type
# in inspect._get_parser is done incorrectly.
def test_attr_from_custom_type_without_parser_fails() -> None:
    with pytest.raises(AssertionError):
        attr_from(
            cls=Bar,
            kwargs={"foo": ""},
            parsers={},
        )


def test_list_parser() -> None:
    parser = list_parser(Foo, List[int], {})
    assert parser("") == []
    assert parser("1,2,3") == [1, 2, 3]


def test_set_parser() -> None:
    parser = set_parser(Foo, Set[int], {})
    assert parser("{}") == set()
    assert parser("{1,2,3}") == {1, 2, 3}
    assert parser("{1,1,2,3}") == {1, 2, 3}


def test_tuple_parser() -> None:
    parser = tuple_parser(Foo, Tuple[int, str], {})
    assert parser("()") == ()
    assert parser("(1,a)") == (1, "a")


def test_dict_parser() -> None:
    parser = dict_parser(Foo, Dict[int, str], {})
    assert parser("{}") == {}
    assert parser("{123;a}") == {123: "a"}


def test_dict_parser_with_duplicate_keys() -> None:
    parser = dict_parser(Foo, Dict[int, str], {})
    with pytest.raises(ValueError):
        parser("{123;a,123;b}")
