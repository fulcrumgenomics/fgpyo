from dataclasses import fields
from typing import Any

from fgpyo.util.inspect import DataclassInstance


class DataSubclassMixin:
    """
    Support construction from an instance of a sub-classed dataclass's parent.
    """

    @classmethod
    def from_parent(cls, parent: DataclassInstance, **kwargs: Any) -> DataclassInstance:
        """
        Construct a subclass instance from an instance of its parent.

        Args:
            parent: An instance of the parent dataclass.

        Returns:
            An instance of the subclass, with the same fields as the parent.
        """
        if not issubclass(cls, type(parent)):
            raise TypeError(f"{cls.__name__} must be a subclass of {type(parent).__name__}")

        parent_fields = {field.name: getattr(parent, field.name) for field in fields(parent)}

        return cls(**parent_fields, **kwargs)
