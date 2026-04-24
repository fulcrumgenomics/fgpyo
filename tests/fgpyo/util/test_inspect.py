import dataclasses
from typing import Optional

import attr
import pytest

from fgpyo.util.inspect import _attribute_has_default
from fgpyo.util.inspect import _attribute_is_optional
from fgpyo.util.inspect import attr_from
from fgpyo.util.inspect import dict_parser
from fgpyo.util.inspect import get_fields
from fgpyo.util.inspect import get_fields_dict
from fgpyo.util.inspect import is_attr_class
from fgpyo.util.inspect import is_dataclasses_class
from fgpyo.util.inspect import list_parser
from fgpyo.util.inspect import set_parser
from fgpyo.util.inspect import tuple_parser


@attr.s(auto_attribs=True, frozen=True)
class Name:
    """Test attr class with various field types."""

    required: str
    custom_parser: str
    converted: int = attr.field(converter=int)
    optional_no_default: Optional[str]
    optional_with_default_none: Optional[str] = None
    optional_with_default_some: Optional[str] = "foo"


def test_attr_from() -> None:
    name = attr_from(
        cls=Name,
        kwargs={"required": "required", "custom_parser": "before", "converted": "42"},
        parsers={str: lambda value: "after" if value == "before" else value},
    )
    assert name.required == "required"
    assert name.custom_parser == "after"
    assert name.converted == 42
    assert name.optional_no_default is None
    assert name.optional_with_default_none is None
    assert name.optional_with_default_some == "foo"


def test_attribute_is_optional() -> None:
    fields_dict = attr.fields_dict(Name)
    assert not _attribute_is_optional(fields_dict["required"])
    assert not _attribute_is_optional(fields_dict["custom_parser"])
    assert not _attribute_is_optional(fields_dict["converted"])
    assert _attribute_is_optional(fields_dict["optional_no_default"])
    assert _attribute_is_optional(fields_dict["optional_with_default_none"])
    assert _attribute_is_optional(fields_dict["optional_with_default_some"])


def test_attribute_has_default() -> None:
    fields_dict = attr.fields_dict(Name)
    assert not _attribute_has_default(fields_dict["required"])
    assert not _attribute_has_default(fields_dict["custom_parser"])
    assert not _attribute_has_default(fields_dict["converted"])
    assert _attribute_has_default(fields_dict["optional_no_default"])
    assert _attribute_has_default(fields_dict["optional_with_default_none"])
    assert _attribute_has_default(fields_dict["optional_with_default_some"])


class Foo:
    """Test class used as a field type."""


@attr.s(auto_attribs=True, frozen=True)
class Bar:
    """Test attr class with a Foo field."""

    foo: Foo


@dataclasses.dataclass(frozen=True)
class Baz:
    """Test dataclass with a Foo field."""

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
    parser = list_parser(Foo, list[int], {})
    assert parser("") == []
    assert parser("1,2,3") == [1, 2, 3]


def test_set_parser() -> None:
    parser = set_parser(Foo, set[int], {})
    assert parser("{}") == set()
    assert parser("{1,2,3}") == {1, 2, 3}
    assert parser("{1,1,2,3}") == {1, 2, 3}


def test_tuple_parser() -> None:
    parser = tuple_parser(Foo, tuple[int, str], {})
    assert parser("()") == ()
    assert parser("(1,a)") == (1, "a")


def test_dict_parser() -> None:
    parser = dict_parser(Foo, dict[int, str], {})
    assert parser("{}") == {}
    assert parser("{123;a}") == {123: "a"}


def test_dict_parser_with_duplicate_keys() -> None:
    parser = dict_parser(Foo, dict[int, str], {})
    with pytest.raises(ValueError):
        parser("{123;a,123;b}")


def test_non_data_class_fails() -> None:
    class NonDataClass:
        x: int

    with pytest.raises(TypeError):
        get_fields_dict(NonDataClass)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        get_fields(NonDataClass)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        attr_from(cls=NonDataClass, kwargs={"x": "1"}, parsers={int: int})


def test_is_attrs_is_dataclasses() -> None:
    assert not is_attr_class(Foo)
    assert not is_dataclasses_class(Foo)

    assert is_attr_class(Bar)
    assert not is_dataclasses_class(Bar)
    assert is_dataclasses_class(Baz)
    assert not is_attr_class(Baz)
