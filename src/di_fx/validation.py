"""
Validation functionality for dependency injection framework.

This module provides validation for dependency graphs to catch
missing dependencies before the application starts.
"""

from typing import Any

from .provide import Provider


class DependencyError(Exception):
    """Raised when there are dependency resolution issues."""

    pass


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


def validate_dependency_graph(providers: dict[type[Any], Provider]) -> None:
    """Validate that all dependencies can be resolved.

    Args:
        providers: Dictionary of type -> provider mappings

    Raises:
        ValidationError: If there are dependency resolution issues
    """
    errors = []

    # Check each provider's dependencies
    for provider_type, provider in providers.items():
        for dep_type in provider.dependencies:
            if dep_type not in providers:
                # Handle Named types in error messages
                if hasattr(dep_type, "name") and hasattr(dep_type, "type"):
                    # This is a Named type
                    dep_name = f"{dep_type.name}:{dep_type.type.__name__}"
                else:
                    # Regular type
                    dep_name = getattr(dep_type, "__name__", str(dep_type))

                # Handle provider type names
                if hasattr(provider_type, "name") and hasattr(provider_type, "type"):
                    # This is a Named type
                    provider_name = (
                        f"{provider_type.name}:{provider_type.type.__name__}"
                    )
                else:
                    # Regular type
                    provider_name = getattr(
                        provider_type, "__name__", str(provider_type)
                    )

                errors.append(
                    f"Provider {provider_name} depends on {dep_name}, "
                    f"but no provider is registered for {dep_name}"
                )

    # Check for circular dependencies
    circular_errors = _check_circular_dependencies(providers)
    errors.extend(circular_errors)

    if errors:
        raise ValidationError(f"Validation failed with {len(errors)} error(s):", errors)


def _check_circular_dependencies(providers: dict[type[Any], Provider]) -> list[str]:
    """Check for circular dependencies in the provider graph."""
    errors = []

    for provider_type in providers:
        visited: set[type[Any]] = set()
        if _has_circular_dependency(provider_type, providers, visited, set()):
            errors.append(
                f"Circular dependency detected involving {provider_type.__name__}"
            )

    return errors


def _has_circular_dependency(
    current_type: type[Any],
    providers: dict[type[Any], Provider],
    visited: set[type[Any]],
    recursion_stack: set[type[Any]],
) -> bool:
    """Check if there's a circular dependency from the current type."""
    if current_type in recursion_stack:
        return True

    if current_type not in providers:
        return False

    if current_type in visited:
        return False

    visited.add(current_type)
    recursion_stack.add(current_type)

    provider = providers[current_type]
    for dep_type in provider.dependencies:
        if _has_circular_dependency(dep_type, providers, visited, recursion_stack):
            return True

    recursion_stack.remove(current_type)
    return False
