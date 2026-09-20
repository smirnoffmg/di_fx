"""
Validation functionality for dependency injection framework.

This module provides validation for dependency graphs to catch
missing dependencies before the application starts.
"""

from typing import Any

from .dotgraph import DotGraph
from .lifecycle import Lifecycle
from .named import get_named_type_info, is_named_type
from .provide import Provider
from .shutdowner import Shutdowner

#: Types the resolver supplies on its own, without a registered provider.
BUILTIN_TYPES: tuple[type[Any], ...] = (Lifecycle, DotGraph, Shutdowner)


class DependencyError(Exception):
    """Raised when there are dependency resolution issues."""

    pass


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


class DuplicateProviderError(ValidationError):
    """Raised when two providers claim the same type."""

    def __init__(self, type_: Any, existing: Any, incoming: Any) -> None:
        message = (
            f"Two providers registered for type {type_name(type_)}: "
            f"{constructor_name(existing)} and {constructor_name(incoming)}"
        )
        super().__init__(message, [message])


def type_name(type_: Any) -> str:
    """Render a dependency key the way a user wrote it."""
    named = get_named_type_info(type_)
    if named is not None:
        name, base_type = named
        return f"{name}:{base_type.__name__}"
    return str(getattr(type_, "__name__", type_))


def constructor_name(provider: Any) -> str:
    return str(getattr(provider.constructor, "__name__", provider.constructor))


def can_resolve(
    dep_type: Any,
    providers: dict[type[Any], Provider],
    values: dict[type[Any], Any],
) -> bool:
    """Whether the resolver would be able to produce this dependency.

    The resolver answers from providers, supplied values, its built-in services and
    the base type behind a Named type. Validation has to ask the same question, or
    it rejects graphs that run and accepts graphs that do not.
    """
    if dep_type in providers or dep_type in values:
        return True
    if dep_type in BUILTIN_TYPES:
        return True
    if is_named_type(dep_type):
        named = get_named_type_info(dep_type)
        return named is not None and named[1] in providers
    return False


def validate_dependency_graph(
    providers: dict[type[Any], Provider],
    values: dict[type[Any], Any] | None = None,
    invokables: list[Any] | None = None,
) -> None:
    """Validate that all dependencies can be resolved.

    Args:
        providers: Dictionary of type -> provider mappings
        values: Dictionary of type -> supplied value mappings
        invokables: Functions that will run at startup

    Raises:
        ValidationError: If there are dependency resolution issues
    """
    values = values or {}
    errors: list[str] = []

    for provider_type, provider in providers.items():
        for dep_type in provider.dependencies:
            if not can_resolve(dep_type, providers, values):
                errors.append(
                    f"Provider {type_name(provider_type)} depends on "
                    f"{type_name(dep_type)}, but no provider is registered for "
                    f"{type_name(dep_type)}"
                )

    for invokable in invokables or []:
        for dep_type in invokable.dependencies:
            if not can_resolve(dep_type, providers, values):
                errors.append(
                    f"Invokable {invokable.name} depends on {type_name(dep_type)}, "
                    f"but no provider is registered for {type_name(dep_type)}"
                )

    errors.extend(_check_circular_dependencies(providers))

    if errors:
        raise ValidationError(f"Validation failed with {len(errors)} error(s):", errors)


def _check_circular_dependencies(providers: dict[type[Any], Provider]) -> list[str]:
    """Report every dependency cycle once, naming only the types on it."""
    finished: set[Any] = set()
    seen_cycles: set[frozenset[Any]] = set()
    errors: list[str] = []

    for provider_type in providers:
        for cycle in _find_cycles(provider_type, providers, finished, []):
            key = frozenset(cycle)
            if key in seen_cycles:
                continue
            seen_cycles.add(key)
            path = " -> ".join(type_name(t) for t in [*cycle, cycle[0]])
            errors.append(f"Circular dependency detected: {path}")

    return errors


def _find_cycles(
    current_type: Any,
    providers: dict[type[Any], Provider],
    finished: set[Any],
    stack: list[Any],
) -> list[list[Any]]:
    if current_type in stack:
        # The cycle is the tail of the current path, not the whole path: the types
        # that merely lead into it are not part of it.
        return [stack[stack.index(current_type) :]]

    if current_type in finished or current_type not in providers:
        return []

    stack.append(current_type)
    cycles: list[list[Any]] = []
    for dep_type in providers[current_type].dependencies:
        cycles.extend(_find_cycles(dep_type, providers, finished, stack))
    stack.pop()

    if not cycles:
        finished.add(current_type)
    return cycles
