"""
Invoke functionality for dependency injection framework.

This module provides the Invoke class for registering startup initialization
functions that run after dependency injection resolution.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Invokable:
    """A function that will be invoked during application startup."""

    func: Callable[..., Any]
    name: str | None = None
    dependencies: list[type[Any]] | None = None

    def __post_init__(self) -> None:
        if not callable(self.func):
            raise ValueError("Invokable must be callable")
        if self.name is None:
            self.name = self.func.__name__
        if self.dependencies is None:
            self.dependencies = []


class Invoke:
    """Container for registering startup initialization functions."""

    def __init__(self, *functions: Callable[..., Any]) -> None:
        self._invokables: list[Invokable] = []

        for func in functions:
            self._register_function(func)

    def _register_function(self, func: Callable[..., Any]) -> None:
        """Register a function to be invoked during startup."""
        import inspect

        sig = inspect.signature(func)
        dependencies = []

        # Extract parameter types for dependency injection
        for param in sig.parameters.values():
            if param.annotation != inspect.Signature.empty:
                # Handle Annotated types - extract the base type
                if (
                    hasattr(param.annotation, "__origin__")
                    and param.annotation.__origin__ is not None
                ):
                    # This is a generic type like Annotated
                    if param.annotation.__origin__.__name__ == "Annotated":
                        # For Annotated[T, ...], use the first type argument as the base type
                        base_type = param.annotation.__args__[0]
                        dependencies.append(base_type)
                    else:
                        dependencies.append(param.annotation)
                else:
                    # Handle Named types - keep them as-is for proper resolution
                    dependencies.append(param.annotation)

        invokable = Invokable(
            func=func,
            name=func.__name__,
            dependencies=dependencies,
        )

        self._invokables.append(invokable)

    def get_invokables(self) -> list[Invokable]:
        """Get all registered invokable functions."""
        return self._invokables.copy()

    def __len__(self) -> int:
        return len(self._invokables)

    def __iter__(self) -> Any:
        return iter(self._invokables)
