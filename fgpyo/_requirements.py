"""Enforce requirements."""

from typing import Callable


class RequirementError(Exception):
    """Exception raised when a requirement is not satisfied."""


def require(condition: bool, message: str | Callable[[], str] | None = None) -> None:
    """Require a condition be satisfied.

    Args:
        condition: The condition to satisfy.
        message: An optional message to include with the error when the condition is false.
            The message may be provided as either a string literal or a function returning a string.
            The function will not be evaluated unless the condition is false.

    Raises:
        RequirementError: If the condition is false.
    """
    if not condition:
        if message is None:
            raise RequirementError()
        elif isinstance(message, str):
            raise RequirementError(message)
        else:
            raise RequirementError(message())
