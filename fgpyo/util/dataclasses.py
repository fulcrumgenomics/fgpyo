from dataclasses import Field
from dataclasses import fields
from typing import Any
from typing import ClassVar
from typing import Dict
from typing import Protocol


class DataclassInstance(Protocol):
    """
    Type hint for a non-specific instance of a dataclass.

    `DataclassReader` is an iterator over instances of the specified dataclass type. However, the
    actual type is not known prior to instantiation. This `Protocol` is used to type hint the return
    signature of `DataclassReader`'s `__next__` method.

    https://stackoverflow.com/a/55240861
    """

    __dataclass_fields__: ClassVar[Dict[str, Field]]


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
