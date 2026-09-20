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
        dependency_errors = _validate_provider_dependencies(provider_type, provider, providers)
        errors.extend(dependency_errors)

    # Check for circular dependencies
    circular_errors = _check_circular_dependencies(providers)
    errors.extend(circular_errors)

    # Check for provider conflicts
    conflict_errors = _check_provider_conflicts(providers)
    errors.extend(conflict_errors)

    if errors:
        raise ValidationError(f"Validation failed with {len(errors)} error(s):", errors)


def _validate_provider_dependencies(
    provider_type: type[Any],
    provider: Provider,
    all_providers: dict[type[Any], Provider],
    visited: set[type[Any]] | None = None
) -> list[str]:
    """Validate dependencies for a specific provider."""
    if visited is None:
        visited = set()
    
    errors: list[str] = []
    
    # Prevent infinite recursion by tracking visited types
    if provider_type in visited:
        return errors
    
    visited.add(provider_type)
    
    for dep_type in provider.dependencies:
        if dep_type not in all_providers:
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
        else:
            # Check if the dependency provider has its own dependencies
            dep_provider = all_providers[dep_type]
            if dep_provider.dependencies and dep_type not in visited:
                # Recursively validate dependency's dependencies
                nested_errors = _validate_provider_dependencies(dep_type, dep_provider, all_providers, visited)
                if nested_errors:
                    errors.extend(nested_errors)

    return errors


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
            recursion_stack.remove(current_type)
            return True

    recursion_stack.remove(current_type)
    return False


def _check_provider_conflicts(providers: dict[type[Any], Provider]) -> list[str]:
    """Check for conflicts between providers."""
    errors = []

    # Check for duplicate providers for the same type
    type_counts: dict[type[Any], int] = {}
    for provider_type in providers:
        type_counts[provider_type] = type_counts.get(provider_type, 0) + 1

    for provider_type, count in type_counts.items():
        if count > 1:
            errors.append(
                f"Multiple providers registered for type {provider_type.__name__} ({count} providers)"
            )

    return errors


def validate_service_contract(provider: Provider) -> list[str]:
    """Validate a service provider contract."""
    errors = []

    # Check constructor is callable
    if not callable(provider.constructor):
        errors.append("Constructor must be callable")

    # Check return type annotation
    if getattr(provider.return_type, "__name__", "") == "Any":
        errors.append("Return type should be specific, not Any")

    # Check dependencies
    for dep_type in provider.dependencies:
        if getattr(dep_type, "__name__", "") == "Any":
            errors.append("Dependency types should be specific, not Any")

    return errors


def get_validation_summary(providers: dict[type[Any], Provider]) -> dict[str, Any]:
    """Get a summary of the validation state."""
    total_providers = len(providers)
    total_dependencies = sum(len(p.dependencies) for p in providers.values())

    # Count async vs sync constructors
    async_count = 0
    sync_count = 0

    for provider in providers.values():
        if hasattr(provider.constructor, "__code__"):
            if provider.constructor.__code__.co_flags & 0x80:  # CO_COROUTINE flag
                async_count += 1
            else:
                sync_count += 1

    # Extract dependency types safely
    dependency_types = []
    for provider in providers.values():
        for dep_type in provider.dependencies:
            if hasattr(dep_type, "__name__"):
                dependency_types.append(dep_type.__name__)
            else:
                dependency_types.append(str(dep_type))

    return {
        "total_providers": total_providers,
        "total_dependencies": total_dependencies,
        "async_constructors": async_count,
        "sync_constructors": sync_count,
        "provider_types": [t.__name__ if hasattr(t, "__name__") else str(t) for t in providers.keys()],
        "dependency_types": list(set(dependency_types))
    }
