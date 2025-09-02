"""
Value supply for dependency injection framework.

This module provides the Supply class for providing configuration values
and constants.
"""

from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T", bound=Any)


@dataclass
class Value:
    """A value that can be injected into services."""

    value: Any
    type_: type[Any]
    name: str = ""


class Supply:
    """Container for providing configuration values and constants."""

    def __init__(self, *values: Any) -> None:
        self._values: dict[type[Any], Value] = {}

        for value in values:
            self._register_value(value)

    def _register_value(self, value: Any) -> None:
        """Register a value for injection."""
        value_type = type(value)

        # Handle special case for dataclasses and custom classes
        if hasattr(value, "__class__") and value.__class__ is not type:
            value_type = value.__class__

        self._values[value_type] = Value(
            value=value, type_=value_type, name=value_type.__name__
        )

    def get_value(self, type_: type[T]) -> T:
        """Get a value of a specific type."""
        if type_ not in self._values:
            raise KeyError(f"No value registered for type {type_.__name__}")
        return self._values[type_].value  # type: ignore

    def has_value(self, type_: type[T]) -> bool:
        """Check if a value exists for a type."""
        return type_ in self._values

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self) -> Any:
        return iter(self._values.values())
