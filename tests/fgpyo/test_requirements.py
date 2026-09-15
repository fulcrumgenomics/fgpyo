import sys

import pytest

from fgpyo import RequirementError
from fgpyo import fail
from fgpyo import require
from fgpyo import require_not_none

if sys.version_info[:2] >= (3, 11):
    from typing import assert_type
else:
    from typing_extensions import assert_type


def _optional_str(value: str | None) -> str | None:
    """Return the value as an `Optional`, hiding its narrowed type from the type checker."""
    return value


def test_require() -> None:
    """Require the requirements."""
    require(True)


def test_require_raises() -> None:
    """Require the requirements."""
    with pytest.raises(RequirementError) as excinfo:
        require(False)

    assert str(excinfo.value) == ""


def test_require_raises_with_message() -> None:
    """Require the requirements."""
    with pytest.raises(RequirementError, match="Message!") as excinfo:
        require(False, message="Message!")

    assert str(excinfo.value) == "Message!"


def test_require_raises_with_message_callable() -> None:
    with pytest.raises(RequirementError, match="Message!") as excinfo:
        require(False, message=lambda: "Message!")

    assert str(excinfo.value) == "Message!"


def test_require_does_not_evaluate_message_when_satisfied() -> None:
    """A callable message is not evaluated when the condition is satisfied."""

    def _message() -> str:
        raise AssertionError("message should not be evaluated")

    require(True, message=_message)


def test_fail_raises() -> None:
    with pytest.raises(RequirementError) as excinfo:
        fail()

    assert str(excinfo.value) == ""


def test_fail_raises_with_message() -> None:
    with pytest.raises(RequirementError, match="Message!") as excinfo:
        fail("Message!")

    assert str(excinfo.value) == "Message!"


def test_fail_raises_with_message_callable() -> None:
    with pytest.raises(RequirementError, match="Message!") as excinfo:
        fail(lambda: "Message!")

    assert str(excinfo.value) == "Message!"


def test_fail_narrows_the_guarded_value() -> None:
    """`fail` returns `NoReturn`, so a guard that calls it narrows the checked expression."""
    value = _optional_str("present")

    if value is None:
        fail()

    assert_type(value, str)
    assert value == "present"


def test_require_not_none_returns_the_value() -> None:
    assert require_not_none("present") == "present"


def test_require_not_none_returns_falsey_values() -> None:
    """Only `None` is rejected; other falsey values are returned unchanged."""
    assert require_not_none("") == ""
    assert require_not_none(0) == 0
    assert require_not_none([]) == []
    assert require_not_none(False) is False


def test_require_not_none_raises() -> None:
    with pytest.raises(RequirementError) as excinfo:
        require_not_none(None)

    assert str(excinfo.value) == ""


def test_require_not_none_raises_with_message() -> None:
    with pytest.raises(RequirementError, match="Message!") as excinfo:
        require_not_none(None, message="Message!")

    assert str(excinfo.value) == "Message!"


def test_require_not_none_raises_with_message_callable() -> None:
    with pytest.raises(RequirementError, match="Message!") as excinfo:
        require_not_none(None, message=lambda: "Message!")

    assert str(excinfo.value) == "Message!"


def test_require_not_none_does_not_evaluate_message_when_satisfied() -> None:
    """A callable message is not evaluated when the value is not `None`."""

    def _message() -> str:
        raise AssertionError("message should not be evaluated")

    require_not_none("present", message=_message)


def test_require_not_none_narrows_the_returned_value() -> None:
    """The return type is narrowed, so the result is usable without a further check."""
    value = _optional_str("present")

    narrowed = require_not_none(value)

    assert_type(narrowed, str)
    assert narrowed == "present"


def test_require_not_none_narrows_in_expression_position() -> None:
    """`require_not_none` narrows inside a comprehension, where a guard does not fit."""
    values = [_optional_str("a"), _optional_str("b")]

    narrowed = [require_not_none(value) for value in values]

    assert_type(narrowed, list[str])
    assert narrowed == ["a", "b"]
