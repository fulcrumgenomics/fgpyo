import sys
import types as python_types
import typing
from typing import Any
from typing import ClassVar
from typing import Dict
from typing import FrozenSet
from typing import Iterable
from typing import List
from typing import Literal
from typing import Mapping
from typing import Protocol
from typing import Tuple
from typing import Type
from typing import Union

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

import dataclasses
import functools
from dataclasses import MISSING as DATACLASSES_MISSING
from dataclasses import fields as get_dataclasses_fields
from dataclasses import is_dataclass as is_dataclasses_class
from enum import Enum
from functools import partial
from pathlib import PurePath
from typing import TYPE_CHECKING
from typing import Callable
from typing import Optional
from typing import TypeVar

import fgpyo.util.types as types

attr: Optional[python_types.ModuleType]
MISSING: FrozenSet[Any]

try:
    import attr

    _use_attr = True
    from attr import fields as get_attr_fields
    from attr import fields_dict as get_attr_fields_dict

    Attribute: TypeAlias = attr.Attribute  # type: ignore[name-defined]
    # dataclasses and attr have internal tokens for missing values, join into a set so that we can
    # check if a value is missing without knowing the type of backing class
    MISSING = frozenset({DATACLASSES_MISSING, attr.NOTHING})
except ImportError:  # pragma: no cover
    _use_attr = False
    attr = None
    Attribute: TypeAlias = TypeVar("Attribute", bound=object)  # type: ignore[misc, no-redef]  # noqa: E501

    # define empty placeholders for getting attr fields as a tuple or dict. They will never be
    # called because the import failed; but they're here to ensure that the function is defined in
    # sections of code that don't know if the import was successful or not.

    def get_attr_fields(cls: type) -> Tuple[dataclasses.Field, ...]:  # type: ignore[misc]
        """Get tuple of fields for attr class. attrs isn't imported so return empty tuple."""
        return ()

    def get_attr_fields_dict(cls: type) -> Dict[str, dataclasses.Field]:  # type: ignore[misc]
        """Get dict of name->field for attr class. attrs isn't imported so return empty dict."""
        return {}

    # for consistency with successful import of attr, create a set for missing values
    MISSING = frozenset({DATACLASSES_MISSING})

if TYPE_CHECKING:  # pragma: no cover
    from _typeshed import DataclassInstance
else:
    # https://github.com/python/typeshed/blob/727f3c4320d2af3af2f16695e24dd78e79b7c070/stdlib/_typeshed/__init__.pyi#L348
    # TODO: update the hint to `Field[Any]` when we drop support for 3.8
    class DataclassInstance(Protocol):
        __dataclasses_fields__: ClassVar[Dict[str, dataclasses.Field]]


if TYPE_CHECKING and _use_attr:  # pragma: no cover
    from attr import AttrsInstance
else:
    # https://github.com/python-attrs/attrs/blob/f7f317ae4c3790f23ae027db626593d50e8a4e88/src/attr/_typing_compat.pyi#L9
    class AttrsInstance(Protocol):  # type: ignore[no-redef]
        __attrs_attrs__: ClassVar[Any]


def is_attr_class(cls: type) -> bool:
    """Return True if the class is an attr class, and False otherwise"""
    return hasattr(cls, "__attrs_attrs__")


_MISSING_OR_NONE: FrozenSet[Any] = frozenset({*MISSING, None})
"""Set of values that are considered missing or None for dataclasses or attr classes"""
_DataclassesOrAttrClass: TypeAlias = Union[DataclassInstance, AttrsInstance]
"""
TypeAlias for dataclasses or attr classes. Mostly nonsense because they are not true types, they
are traits, but there is no python trait-tester.
"""
FieldType: TypeAlias = Union[dataclasses.Field, Attribute]
"""
TypeAlias for dataclass Fields or attrs Attributes. It will correspond to the correct type for the
corresponding _DataclassesOrAttrClass
"""


def _get_dataclasses_fields_dict(
    class_or_instance: Union[DataclassInstance, Type[DataclassInstance]],
) -> Dict[str, dataclasses.Field]:
    """Get a dict from field name to Field for a dataclass class or instance."""
    return {field.name: field for field in get_dataclasses_fields(class_or_instance)}


class ParserNotFoundException(Exception):
    pass


def split_at_given_level(
    field: str,
    split_delim: str = ",",
    increase_depth_chars: Iterable[str] = ("{", "(", "["),
    decrease_depth_chars: Iterable[str] = ("}", ")", "]"),
) -> List[str]:
    """
    Splits a nested field by its outer-most level

    Note that this method may produce incorrect results fields containing strings containing
    unpaired characters that increase or decrease the depth

    Not currently smart enough to deal with fields enclosed in quotes ('' or "") - TODO
    """

    outer_depth_of_split = 0
    current_outer_splits = []
    out_vals: List[str] = []
    for high_level_split in field.split(split_delim):
        increase_in_depth = 0
        for char in increase_depth_chars:
            increase_in_depth += high_level_split.count(char)

        decrease_in_depth = 0
        for char in decrease_depth_chars:
            decrease_in_depth += high_level_split.count(char)
        outer_depth_of_split += increase_in_depth - decrease_in_depth

        assert outer_depth_of_split >= 0, "Unpaired depth character! Likely incorrect output"

        current_outer_splits.append(high_level_split)
        if outer_depth_of_split == 0:
            out_vals.append(split_delim.join(current_outer_splits))
            current_outer_splits = []
    assert outer_depth_of_split == 0, "Unpaired depth character! Likely incorrect output!"
    return out_vals


NoneType: TypeAlias = type(None)  # type: ignore[no-redef]


def list_parser(
    cls: Type, type_: TypeAlias, parsers: Optional[Dict[type, Callable[[str], Any]]] = None
) -> partial:
    """
    Returns a function that parses a stringified list into a `List` of the correct type.

    Args:
        cls: the type of the class object this is being parsed for (used to get default val for
            parsers)
        type_: the type of the attribute to be parsed
        parsers: an optional mapping from type to the function to use for parsing that type (allows
            for parsing of more complex types)
    """
    subtypes = typing.get_args(type_)
    assert len(subtypes) == 1, "Lists are allowed only one subtype per PEP specification!"
    subtype_parser = _get_parser(
        cls,
        subtypes[0],
        parsers,
    )
    return functools.partial(
        lambda s: list(
            []
            if s == ""
            else [subtype_parser(item) for item in list(split_at_given_level(s, split_delim=","))]
        )
    )


def set_parser(
    cls: Type, type_: TypeAlias, parsers: Optional[Dict[type, Callable[[str], Any]]] = None
) -> partial:
    """
    Returns a function that parses a stringified set into a `Set` of the correct type.

    Args:
        cls: the type of the class object this is being parsed for (used to get default val for
            parsers)
        type_: the type of the attribute to be parsed
        parsers: an optional mapping from type to the function to use for parsing that type (allows
            for parsing of more complex types)
    """
    subtypes = typing.get_args(type_)
    assert len(subtypes) == 1, "Sets are allowed only one subtype per PEP specification!"
    subtype_parser = _get_parser(
        cls,
        subtypes[0],
        parsers,
    )
    return functools.partial(
        lambda s: set(
            set({})
            if s == "{}"
            else [
                subtype_parser(item) for item in set(split_at_given_level(s[1:-1], split_delim=","))
            ]
        )
    )


def tuple_parser(
    cls: Type, type_: TypeAlias, parsers: Optional[Dict[type, Callable[[str], Any]]] = None
) -> partial:
    """
    Returns a function that parses a stringified tuple into a `Tuple` of the correct type.

    Args:
        cls: the type of the class object this is being parsed for (used to get default val for
            parsers)
        type_: the type of the attribute to be parsed
        parsers: an optional mapping from type to the function to use for parsing that type (allows
            for parsing of more complex types)
    """
    subtype_parsers = [
        _get_parser(
            cls,
            subtype,
            parsers,
        )
        for subtype in typing.get_args(type_)
    ]

    def tuple_parse(tuple_string: str) -> Tuple[Any, ...]:
        """
        Parses a dictionary value (can do so recursively)
        Note that this tool will fail on tuples containing strings containing
        unpaired '{', or '}' characters
        """
        assert tuple_string[0] == "(", "Tuple val improperly formatted"
        assert tuple_string[-1] == ")", "Tuple val improperly formatted"
        tuple_string = tuple_string[1:-1]
        if len(tuple_string) == 0:
            return ()
        else:
            val_strings = split_at_given_level(tuple_string, split_delim=",")
            return tuple(parser(val_str) for parser, val_str in zip(subtype_parsers, val_strings))

    return functools.partial(tuple_parse)


def dict_parser(
    cls: Type, type_: TypeAlias, parsers: Optional[Dict[type, Callable[[str], Any]]] = None
) -> partial:
    """
    Returns a function that parses a stringified dict into a `Dict` of the correct type.

    Args:
        cls: the type of the class object this is being parsed for (used to get default val for
            parsers)
        type_: the type of the attribute to be parsed
            parsers: an optional mapping from type to the function to use for parsing that type
            (allows for parsing of more complex types)
    """
    subtypes = typing.get_args(type_)
    assert len(subtypes) == 2, "Dict object must have exactly 2 subtypes per PEP specification!"
    (key_parser, val_parser) = (
        _get_parser(
            cls,
            subtypes[0],
            parsers,
        ),
        _get_parser(
            cls,
            subtypes[1],
            parsers,
        ),
    )

    def dict_parse(dict_string: str) -> Dict[Any, Any]:
        """
        Parses a dictionary value (can do so recursively)
        """
        assert dict_string[0] == "{", "Dict val improperly formatted"
        assert dict_string[-1] == "}", "Dict val improprly formatted"
        dict_string = dict_string[1:-1]
        if len(dict_string) == 0:
            return {}
        else:
            outer_splits = split_at_given_level(dict_string, split_delim=",")
            out_dict = {}
            for outer_split in outer_splits:
                inner_splits = split_at_given_level(outer_split, split_delim=";")
                assert (
                    len(inner_splits) % 2 == 0
                ), "Inner splits of dict didn't have matched key val pairs"
                for i in range(0, len(inner_splits), 2):
                    key = key_parser(inner_splits[i])
                    if key in out_dict:
                        raise ValueError("Duplicate key found in dict: {}".format(key))
                    out_dict[key] = val_parser(inner_splits[i + 1])
            return out_dict

    return functools.partial(dict_parse)


def _get_parser(  # noqa: C901
    cls: Type, type_: TypeAlias, parsers: Optional[Dict[type, Callable[[str], Any]]] = None
) -> partial:
    """Attempts to find a parser for a provided type.

    Args:
        cls: the type of the class object this is being parsed for (used to get default val for
        parsers)
        type_: the type of the attribute to be parsed
        parsers: an optional mapping from type to the function to use for parsing that type (allows
        for parsing of more complex types)
    """
    parser: partial[type_]
    if parsers is None:
        parsers = cls._parsers()

    # TODO - handle optional types
    def get_parser() -> partial:  # noqa: C901
        nonlocal type_
        nonlocal parsers
        try:
            return functools.partial(parsers[type_])
        except KeyError as ex:
            if (
                type_ in [str, int, float]
                or isinstance(type_, type)
                and issubclass(type_, PurePath)
            ):
                return functools.partial(type_)
            elif type_ == bool:
                return functools.partial(types.parse_bool)
            elif type_ == list:
                raise ValueError("Unable to parse list (try typing.List[type])") from ex
            elif type_ == tuple:
                raise ValueError("Unable to parse tuple (try typing.Tuple[type])") from ex
            elif type_ == set:
                raise ValueError("Unable to parse set (try typing.Set[type])") from ex
            elif type_ == dict:
                raise ValueError("Unable to parse dict (try typing.Mapping[type])") from ex
            elif typing.get_origin(type_) == list:
                return list_parser(cls, type_, parsers)
            elif typing.get_origin(type_) == set:
                return set_parser(cls, type_, parsers)
            elif typing.get_origin(type_) == tuple:
                return tuple_parser(cls, type_, parsers)
            elif typing.get_origin(type_) == dict:
                return dict_parser(cls, type_, parsers)
            elif isinstance(type_, type) and issubclass(type_, Enum):
                return types.make_enum_parser(type_)
            elif types.is_constructible_from_str(type_):
                return functools.partial(type_)
            elif type_ == NoneType:
                return functools.partial(types.none_parser)
            elif typing.get_origin(type_) is Union:
                return types.make_union_parser(
                    union=type_,
                    parsers=[_get_parser(cls, arg, parsers) for arg in typing.get_args(type_)],
                )
            elif typing.get_origin(type_) is Literal:
                return types.make_literal_parser(
                    type_,
                    [_get_parser(cls, type(arg), parsers) for arg in typing.get_args(type_)],
                )
            else:
                raise ParserNotFoundException(
                    "no parser found for type {}".format(
                        # typing types have no __name__.
                        getattr(type_, "__name__", repr(type_))
                    )
                ) from ex

    parser = get_parser()
    # Set the name that the user expects to see in error messages (we always
    # return a temporary partial object so it's safe to set its __name__).
    # Unions and Literals don't have a __name__, but their str is fine.
    setattr(parser, "__name__", getattr(type_, "__name__", str(type_)))  # noqa: B010
    return parser


def get_fields_dict(
    cls: Union[_DataclassesOrAttrClass, Type[_DataclassesOrAttrClass]],
) -> Mapping[str, FieldType]:
    """Get the fields dict from either a dataclasses or attr dataclass (or instance)"""
    if is_dataclasses_class(cls):
        return _get_dataclasses_fields_dict(cls)
    elif is_attr_class(cls):  # type: ignore[arg-type]
        return get_attr_fields_dict(cls)  # type: ignore[arg-type]
    else:
        raise TypeError("cls must a dataclasses or attr class")


def get_fields(
    cls: Union[_DataclassesOrAttrClass, Type[_DataclassesOrAttrClass]],
) -> Tuple[FieldType, ...]:
    """Get the fields tuple from either a dataclasses or attr dataclass (or instance)"""
    if is_dataclasses_class(cls):
        return get_dataclasses_fields(cls)
    elif is_attr_class(cls):  # type: ignore[arg-type]
        return get_attr_fields(cls)  # type: ignore[arg-type, no-any-return]
    else:
        raise TypeError("cls must a dataclasses or attr class")


_AttrFromType = TypeVar("_AttrFromType")
"""TypeVar to allow attr_from to be used with either an attr class or a dataclasses class"""


def attr_from(
    cls: Type[_AttrFromType],
    kwargs: Dict[str, str],
    parsers: Optional[Dict[type, Callable[[str], Any]]] = None,
) -> _AttrFromType:
    """Builds an attr or dataclasses class from key-word arguments

    Args:
        cls: the attr or dataclasses class to be built
        kwargs: a dictionary of keyword arguments
        parsers: a dictionary of parser functions to apply to specific types

    """
    return_values: Dict[str, Any] = {}
    for attribute in get_fields(cls):  # type: ignore[arg-type]
        return_value: Any
        if attribute.name in kwargs:
            str_value: str = kwargs[attribute.name]
            set_value: bool = False

            # Use the converter if provided
            converter = getattr(attribute, "converter", None)
            if converter is not None:
                return_value = converter(str_value)
                set_value = True

            # try getting a known parser
            if not set_value:
                try:
                    parser = _get_parser(cls=cls, type_=attribute.type, parsers=parsers)
                    return_value = parser(str_value)
                    set_value = True
                except ParserNotFoundException:
                    pass

            # try setting by casting
            # Note that while bools *can* be cast from string, all non-empty strings evaluate to
            # True, because python, so we need to check for that explicitly
            if not set_value and attribute.type is not None and not attribute.type == bool:
                try:
                    return_value = attribute.type(str_value)
                    set_value = True
                except (ValueError, TypeError):
                    pass

            # fail otherwise
            assert (
                set_value
            ), f"Do not know how to convert string to {attribute.type} for value: {str_value}"
        else:  # no value, check for a default
            assert attribute.default is not None or _attribute_is_optional(
                attribute
            ), f"No value given and no default for attribute `{attribute.name}`"
            return_value = attribute.default
            # when the default is attr.NOTHING, just use None
            if return_value in MISSING:
                return_value = None

        return_values[attribute.name] = return_value

    return cls(**return_values)


def _attribute_is_optional(attribute: FieldType) -> bool:
    """Returns True if the attribute is optional, False otherwise"""
    return typing.get_origin(attribute.type) is Union and isinstance(
        None, typing.get_args(attribute.type)
    )


def _attribute_has_default(attribute: FieldType) -> bool:
    """Returns True if the attribute has a default value, False otherwise"""
    return attribute.default not in _MISSING_OR_NONE or _attribute_is_optional(attribute)
