"""Enforce requirements."""

from typing import Optional


class RequirementError(ValueError):
    """Exception raised when a requirement is not satisfied."""


def require(condition: bool, msg: Optional[str] = None) -> None:
    """Require a condition be satisfied.

    Args:
        condition: The condition to satisfy.
        msg: An optional message to include with the error when the condition is false.

    Raises:
        RequirementError: If the condition is false.
    """
    if not condition:
        if msg is not None:
            raise RequirementError(msg)
        else:
            raise RequirementError
