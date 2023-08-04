from typing import Optional

import attr

from fgpyo.util.inspect import attr_from
from fgpyo.util.inspect import attribute_has_default
from fgpyo.util.inspect import attribute_is_optional


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
