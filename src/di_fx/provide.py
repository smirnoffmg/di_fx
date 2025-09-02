"""
Provider registration for dependency injection framework.

This module provides the Provide class for registering service constructors.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from .annotate import As

T = TypeVar("T", bound=Any)


@dataclass
class Provider:
    """A service provider that can construct instances of a type."""

    constructor: Callable[..., Any]
    return_type: type[Any]
    dependencies: list[type[Any]]
    singleton: bool = True

    def __post_init__(self) -> None:
        if not callable(self.constructor):
            raise ValueError("Constructor must be callable")


class Provide:
    """Container for registering service providers."""

    def __init__(self, *constructors: Callable[..., Any]) -> None:
        self._providers: dict[type[Any], Provider] = {}

        for constructor in constructors:
            self._register_constructor(constructor)

    def _register_constructor(self, constructor: Callable[..., Any]) -> None:
        """Register a constructor function."""
        # Handle Annotate tuples (constructor, annotations)
        if isinstance(constructor, tuple) and len(constructor) == 2:
            actual_constructor, annotations = constructor
            if callable(actual_constructor) and isinstance(annotations, list):
                # Register the main constructor
                self._register_constructor_internal(actual_constructor)

                # Register for each interface type
                for annotation in annotations:
                    if isinstance(annotation, As):
                        self._providers[annotation.interface_type] = Provider(
                            constructor=actual_constructor,
                            return_type=annotation.interface_type,
                            dependencies=self._get_dependencies(actual_constructor),
                        )
                return

        # Regular constructor
        self._register_constructor_internal(constructor)

    def _register_constructor_internal(self, constructor: Callable[..., Any]) -> None:
        """Internal method to register a constructor function."""
        # Extract return type annotation if available
        import inspect

        sig = inspect.signature(constructor)
        return_annotation = sig.return_annotation

        if return_annotation == inspect.Signature.empty:
            raise ValueError(
                f"Constructor {constructor.__name__} must have return type annotation"
            )

        # Extract parameter types
        dependencies = self._get_dependencies(constructor)

        provider = Provider(
            constructor=constructor,
            return_type=return_annotation,
            dependencies=dependencies,
        )

        self._providers[return_annotation] = provider

        # Handle generic types like AsyncIterator[T] - also register for T
        if (
            hasattr(return_annotation, "__origin__")
            and return_annotation.__origin__ is not None
        ):
            # This is a generic type, extract the inner type
            args = getattr(return_annotation, "__args__", [])
            if args:
                inner_type = args[0]
                if inner_type != Any:
                    # Create a provider that resolves the inner type from the generic
                    inner_provider = Provider(
                        constructor=constructor,
                        return_type=inner_type,
                        dependencies=dependencies,
                    )
                    self._providers[inner_type] = inner_provider

    def _get_dependencies(self, constructor: Callable[..., Any]) -> list[type[Any]]:
        """Extract dependencies from a constructor function."""
        import inspect

        dependencies = []
        sig = inspect.signature(constructor)

        for param in sig.parameters.values():
            if param.annotation != inspect.Signature.empty:
                dependencies.append(param.annotation)

        return dependencies

    def get_provider(self, type_: type[Any]) -> Provider:
        """Get a provider for a specific type."""
        if type_ not in self._providers:
            raise KeyError(f"No provider registered for type {type_.__name__}")
        return self._providers[type_]

    def has_provider(self, type_: type[Any]) -> bool:
        """Check if a provider exists for a type."""
        return type_ in self._providers

    def __len__(self) -> int:
        return len(self._providers)

    def __iter__(self) -> Any:
        return iter(self._providers.values())
