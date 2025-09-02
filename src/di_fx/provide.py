"""
Provider registration for dependency injection framework.

This module provides the Provide class for registering service constructors.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from .annotate import As
from .component import Component

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


class Provide(Component):
    """Container for registering service providers."""

    def __init__(self, *constructors: Callable[..., Any]) -> None:
        super().__init__()
        self._providers: dict[type[Any], Provider] = {}

        for constructor in constructors:
            self._register_constructor(constructor)

    def _register_constructor(self, constructor: Callable[..., Any]) -> None:
        """Register a constructor function."""
        # Handle Annotate tuples (constructor, annotations)
        if isinstance(constructor, tuple) and len(constructor) == 2:  # type: ignore[unreachable]
            actual_constructor, annotations = constructor  # type: ignore[unreachable]
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
                # Early return for valid tuple format
                return

        # Regular constructor (including invalid tuple formats)
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
        """Extract dependency types from constructor signature."""
        import inspect

        sig = inspect.signature(constructor)
        dependencies = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = param.annotation
            if param_type == inspect.Signature.empty:
                raise ValueError(
                    f"Parameter {param_name} in {constructor.__name__} must have type annotation"
                )

            dependencies.append(param_type)

        return dependencies

    def get_providers(self) -> list[Any]:
        """Get all providers registered in this Provide component."""
        return list(self._providers.values())

    def get_supplies(self) -> list[Any]:
        """Provide components don't contain supplies."""
        return []

    def get_invokables(self) -> list[Any]:
        """Provide components don't contain invokables."""
        return []

    def __getitem__(self, type_: type[T]) -> Provider:
        """Get a provider for a specific type."""
        if type_ not in self._providers:
            raise KeyError(f"No provider registered for type {type_}")
        return self._providers[type_]

    def __contains__(self, type_: type[Any]) -> bool:
        """Check if a provider exists for a type."""
        return type_ in self._providers

    def __iter__(self) -> Any:
        """Iterate over registered providers."""
        return iter(self._providers.values())

    def __len__(self) -> int:
        """Get the number of registered providers."""
        return len(self._providers)

    def get_provider_types(self) -> list[type[Any]]:
        """Get all types that have providers registered."""
        return list(self._providers.keys())

    def has_provider_for(self, type_: type[Any]) -> bool:
        """Check if a provider exists for a specific type."""
        return type_ in self._providers

    def get_provider_info(self) -> dict[type[Any], dict[str, Any]]:
        """Get detailed information about all providers."""
        info = {}
        for type_, provider in self._providers.items():
            info[type_] = {
                "constructor": provider.constructor.__name__,
                "dependencies": provider.dependencies,
                "singleton": provider.singleton,
            }
        return info
