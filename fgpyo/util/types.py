import collections
import inspect
import typing
from enum import Enum
from functools import partial
from typing import Callable
from typing import Iterable
from typing import Type
from typing import TypeVar
from typing import Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


# `get_origin_type` is a method that gets the outer type (ex list in a List[str])
if hasattr(typing, "get_origin"):  # py>=38
    get_origin_type = typing.get_origin
else:  # py<38

    def get_origin_type(tp: Type) -> Type:
        """Returns the outer type of a Typing object (ex list in a List[T])"""
        import typing_inspect

        if type(tp) is type(Literal):  # Py<=3.6.
            return Literal
        origin = typing_inspect.get_origin(tp)
        return {
            typing.List: list,
            typing.Iterable: collections.abc.Iterable,
            typing.Sequence: collections.abc.Sequence,
            typing.Tuple: tuple,
            typing.Set: set,
            typing.Mapping: dict,
            typing.Dict: dict,
        }.get(origin, origin)


# `get_origin_type` is a method that gets the inner type (ex str in a List[str])
if hasattr(typing, "get_args"):  # py>=38
    get_arg_types = typing.get_args
else:  # py<38

    def get_arg_types(tp: Type) -> Type:
        """Gets the inner types of a Typing object (ex T in a List[T])"""
        import typing_inspect

        if type(tp) is type(Literal):  # Py<=3.6.
            return tp.__values__
        return typing_inspect.get_args(tp, evaluate=True)  # evaluate=True default on Py>=3.7.


T = TypeVar("T")
UnionType = TypeVar("UnionType", bound="Union")
EnumType = TypeVar("EnumType", bound="Enum")
LiteralType = TypeVar("LiteralType", bound="Literal")


class InspectException(Exception):
    pass


def parse_bool(string: str) -> bool:
    """Parses strings into bools accounting for the many different text representations of bools
    that can be used
    """
    if string.lower() in ["t", "true", "1"]:
        return True
    elif string.lower() in ["f", "false", "0"]:
        return False
    else:
        raise ValueError("{} is not a valid boolean string".format(string))


def _make_enum_parser_worker(enum: Type[EnumType], value: str) -> EnumType:
    """Worker function behind enum parsing. Takes enum type and creates an instance of the enum
    from a string if possible"""
    try:
        return enum(value)
    except KeyError:
        raise InspectException(
            "invalid choice: {!r} (choose from {})".format(
                value, ", ".join(map(repr, enum.__members__))
            )
        )


def make_enum_parser(enum: Type[EnumType]) -> partial:
    """Makes a parser function for enum classes"""
    return partial(_make_enum_parser_worker, enum)


def is_constructible_from_str(type_: T) -> bool:
    """Returns true if the provided type can be constructed from a string"""
    try:
        sig = inspect.signature(type_)
        ((argname, _),) = sig.bind(object()).arguments.items()
    except TypeError:  # Can be raised by signature() or Signature.bind().
        return False
    except ValueError:
        # Can be raised for classes, if the relevant info is in `__init__`.
        if not isinstance(type_, type):
            raise
    else:
        if sig.parameters[argname].annotation is str:
            return True
    # FIXME
    # if isinstance(type_, type):
    #     # signature() first checks __new__, if it is present.
    #     return _is_constructible_from_str(type_.__init__(object(), type_))
    return False


def _is_optional(type_: T) -> bool:
    """Returns true if type_ is optional"""
    return get_origin_type(type_) is Union and type(None) in get_arg_types(type_)


def _make_union_parser_worker(
    union: Type[UnionType],
    parsers: Iterable[Callable[[str], UnionType]],
    value: str,
) -> T:
    """Worker function behind union parsing. Iterates through possible parsers for the union and
    returns the value produced by the first parser that works. Otherwise raises an error if none
    work"""
    # Need to do this in the case of type Optional[str], because otherwise it'll return the string
    # 'None' instead of the object None
    if _is_optional(union):
        try:
            return none_parser(value)
        except (ValueError, InspectException):
            pass
    for p in parsers:
        try:
            return p(value)
        except (ValueError, InspectException):
            pass
    raise ValueError(f"{value} could not be parsed as any of {union}")


def make_union_parser(union: Type[UnionType], parsers: Iterable[Callable[[str], T]]) -> partial:
    """Generates a parser function for a union type object and set of parsers for the possible
    parsers to that union type object
    """
    return partial(_make_union_parser_worker, union, parsers)


def _make_literal_parser_worker(
    literal: Type[LiteralType], parsers: Iterable[Callable[[str], LiteralType]], value: str
) -> LiteralType:
    """Worker function behind literal parsing. Iterates through possible literals and
    returns the value produced by the first literal that matches expectation.
    Otherwise raises an error if none work"""
    for arg, p in zip(get_arg_types(literal), parsers):
        try:
            if p(value) == arg:
                return arg
        except ValueError:
            pass
    raise InspectException(
        "invalid choice: {!r} (choose from {})".format(
            value, ", ".join(map(repr, map(str, get_arg_types(literal))))
        )
    )


def make_literal_parser(
    literal: Type[LiteralType], parsers: Iterable[Callable[[str], LiteralType]]
) -> partial:
    """Generates a parser function for a literal type object and a set of parsers for the possible
    parsers to that literal type object
    """
    return partial(_make_literal_parser_worker, literal, parsers)


def is_list_like(type_: T) -> bool:
    """Returns true if the value is a list or list like object"""
    return get_origin_type(type_) in [list, collections.abc.Iterable, collections.abc.Sequence]


def none_parser(value: str) -> None:
    """Returns None if the value is 'None', else raises an error"""
    if value == "":
        return None
    raise ValueError(f"NoneType not a valid type for {value}")
