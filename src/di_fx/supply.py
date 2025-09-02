"""
Supply functionality for dependency injection framework.

This module provides the Supply class for providing configuration values
and other static values to the dependency injection system.
"""

from dataclasses import dataclass
from typing import Any, TypeVar

from .component import Component

T = TypeVar("T", bound=Any)


@dataclass
class Value:
    """A value that can be supplied to the DI system."""

    type_: type[Any]
    value: Any

    def __post_init__(self) -> None:
        if not isinstance(self.value, self.type_):
            raise ValueError(f"Value {self.value} is not of type {self.type_}")


class Supply(Component):
    """Container for supplying configuration values and other static values."""

    def __init__(self, *values: Any) -> None:
        super().__init__()
        self._values: dict[type[Any], Value] = {}

        for value in values:
            self._register_value(value)

    def _register_value(self, value: Any) -> None:
        """Register a value in the supply container."""
        if isinstance(value, Value):
            # Already a Value object
            self._values[value.type_] = value
        else:
            # Create a Value object from the raw value
            value_obj = Value(type_=type(value), value=value)
            self._values[type(value)] = value_obj

    def get_providers(self) -> list[Any]:
        """Supply components don't contain providers."""
        return []

    def get_supplies(self) -> list[Any]:
        """Get all values registered in this Supply component."""
        return list(self._values.values())

    def get_invokables(self) -> list[Any]:
        """Supply components don't contain invokables."""
        return []

    def __getitem__(self, type_: type[T]) -> Any:
        """Get a value for a specific type."""
        if type_ not in self._values:
            raise KeyError(f"No value registered for type {type_}")
        return self._values[type_].value

    def __contains__(self, type_: type[Any]) -> bool:
        """Check if a value exists for a type."""
        return type_ in self._values

    def __iter__(self) -> Any:
        """Iterate over registered values."""
        return iter(self._values.values())

    def __len__(self) -> int:
        """Get the number of registered values."""
        return len(self._values)

    def get_value_types(self) -> list[type[Any]]:
        """Get all types that have values registered."""
        return list(self._values.keys())

    def has_value_for(self, type_: type[Any]) -> bool:
        """Check if a value exists for a specific type."""
        return type_ in self._values

    def get_value_info(self) -> dict[type[Any], dict[str, Any]]:
        """Get detailed information about all values."""
        info = {}
        for type_, value in self._values.items():
            info[type_] = {
                "value": value.value,
                "type": value.type_.__name__,
            }
        return info
