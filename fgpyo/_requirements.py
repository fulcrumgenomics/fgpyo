"""Enforce requirements."""

from typing import Optional


class RequirementError(Exception):
    """Exception raised when a requirement is not satisfied."""


def require(condition: bool, message: Optional[str] = None) -> None:
    """Require a condition be satisfied.

    Args:
        condition: The condition to satisfy.
        message: An optional message to include with the error when the condition is false.

    Raises:
        RequirementError: If the condition is false.
    """
    if not condition:
        if message is not None:
            raise RequirementError(message)
        else:
            raise RequirementError()
