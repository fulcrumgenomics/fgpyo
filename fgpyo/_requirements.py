"""Enforce requirements."""

from collections.abc import Callable
from typing import NoReturn
from typing import TypeVar

ValueType = TypeVar("ValueType")


class RequirementError(Exception):
    """Exception raised when a requirement is not satisfied."""


def fail(message: str | Callable[[], str] | None = None) -> NoReturn:
    """
    Raise a `RequirementError`.

    `fail` is annotated as returning `NoReturn`, so a type checker treats any branch that calls it
    as terminating. Unlike `require`, this preserves type narrowing, which makes `fail` a drop-in
    replacement for `assert` when the checked expression must be narrowed:

    ```python
    if read.cigarstring is None:
        fail(lambda: f"Read {read.query_name} is missing a cigar")

    # `read.cigarstring` is narrowed to `str` from here
    ```

    Args:
        message: An optional message to include with the error.
            The message may be provided as either a string literal or a function returning a
            string. `fail` always raises, so a function is evaluated immediately; it is accepted
            for consistency with `require` and `require_not_none`.

    Raises:
        RequirementError: Always.

    Examples:
        >>> try:
        ...     fail("The requirement was not satisfied")
        ... except RequirementError as error:
        ...     print(error)
        The requirement was not satisfied
    """
    if message is None:
        raise RequirementError()
    elif isinstance(message, str):
        raise RequirementError(message)
    else:
        raise RequirementError(message())


def require(condition: bool, message: str | Callable[[], str] | None = None) -> None:
    """
    Require a condition be satisfied.

    `require` does not narrow types, because the condition has already been evaluated to a `bool`
    by the time it is passed. Use `fail` in a guard, or `require_not_none`, when the checked
    expression must be narrowed.

    Args:
        condition: The condition to satisfy.
        message: An optional message to include with the error when the condition is false.
            The message may be provided as either a string literal or a function returning a string.
            The function will not be evaluated unless the condition is false.

    Raises:
        RequirementError: If the condition is false.

    Examples:
        >>> require(True)
        >>> try:
        ...     require(False, "The requirement was not satisfied")
        ... except RequirementError as error:
        ...     print(error)
        The requirement was not satisfied
    """
    if not condition:
        fail(message)


def require_not_none(
    value: ValueType | None,
    message: str | Callable[[], str] | None = None,
) -> ValueType:
    """
    Require a value is not `None`, and return it.

    The returned value is narrowed to `ValueType`, so `require_not_none` may be used in expression
    position, where a statement-level guard does not fit:

    ```python
    query_names = [require_not_none(rec.query_name) for rec in records]
    ```

    Narrowing applies to the returned value, not to the argument. Calling `require_not_none(value)`
    and discarding the result does not narrow `value`.

    Args:
        value: The value to require is not `None`.
        message: An optional message to include with the error when the value is `None`.
            The message may be provided as either a string literal or a function returning a string.
            The function will not be evaluated unless the value is `None`.

    Returns:
        The value, which is not `None`.

    Raises:
        RequirementError: If the value is `None`.

    Examples:
        >>> require_not_none(1)
        1
        >>> try:
        ...     require_not_none(None, "The value must not be None")
        ... except RequirementError as error:
        ...     print(error)
        The value must not be None
    """
    if value is None:
        fail(message)

    return value
