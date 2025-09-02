"""
Invoke functionality for dependency injection framework.

This module provides the Invoke class for registering startup initialization
functions that will be executed when the application starts.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .component import Component


@dataclass
class Invokable:
    """An invokable function that will be executed during startup."""

    func: Callable[..., Any]
    name: str
    dependencies: list[type[Any]]


class Invoke(Component):
    """Container for registering startup initialization functions."""

    def __init__(self, *functions: Callable[..., Any]) -> None:
        super().__init__()
        self._invokables: list[Invokable] = []

        for func in functions:
            self._register_function(func)

    def _register_function(self, func: Callable[..., Any]) -> None:
        """Register a function for invocation during startup."""
        import inspect

        # Extract function signature
        sig = inspect.signature(func)

        # Extract dependencies from parameters
        dependencies = []
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = param.annotation
            if param_type == inspect.Signature.empty:
                raise ValueError(
                    f"Parameter {param_name} in {func.__name__} must have type annotation"
                )

            dependencies.append(param_type)

        # Create invokable
        invokable = Invokable(
            func=func,
            name=func.__name__,
            dependencies=dependencies,
        )

        self._invokables.append(invokable)

    def get_providers(self) -> list[Any]:
        """Invoke components don't contain providers."""
        return []

    def get_supplies(self) -> list[Any]:
        """Invoke components don't contain supplies."""
        return []

    def get_invokables(self) -> list[Any]:
        """Get all invokable functions registered in this Invoke component."""
        return self._invokables.copy()

    def __iter__(self) -> Any:
        """Iterate over registered invokables."""
        return iter(self._invokables)

    def __len__(self) -> int:
        """Get the number of registered invokables."""
        return len(self._invokables)

    def get_invokable_names(self) -> list[str]:
        """Get names of all registered invokable functions."""
        return [invokable.name for invokable in self._invokables]

    def get_invokable_by_name(self, name: str) -> Invokable | None:
        """Get an invokable function by name."""
        for invokable in self._invokables:
            if invokable.name == name:
                return invokable
        return None

    def has_invokable(self, name: str) -> bool:
        """Check if an invokable function exists with the given name."""
        return any(invokable.name == name for invokable in self._invokables)

    def get_invokable_info(self) -> dict[str, dict[str, Any]]:
        """Get detailed information about all invokables."""
        info = {}
        for invokable in self._invokables:
            info[invokable.name] = {
                "function": invokable.func.__name__,
                "dependencies": [dep.__name__ for dep in invokable.dependencies],
                "dependency_count": len(invokable.dependencies),
            }
        return info
