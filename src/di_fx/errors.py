"""Exceptions raised by di_fx."""

from typing import Any


class DiFxError(Exception):
    """Base class for every error di_fx raises."""


class ValidationError(DiFxError):
    """The dependency graph cannot be satisfied."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors if errors is not None else [message]


class MissingProviderError(ValidationError):
    """Nothing in the graph can produce a requested type."""


class DuplicateProviderError(ValidationError):
    """Two providers claim the same type."""

    def __init__(self, type_name: str, first: str, second: str) -> None:
        super().__init__(
            f"Two providers registered for type {type_name}: {first} and {second}"
        )


class CircularDependencyError(ValidationError):
    """A type depends on itself, directly or through other types."""

    def __init__(self, path: list[Any], render: Any = str) -> None:
        names = " -> ".join(render(t) for t in [*path, path[0]])
        super().__init__(f"Circular dependency detected: {names}")
        self.path = path


class LifecycleError(DiFxError):
    """Something went wrong starting or stopping the application."""


class HookTimeoutError(LifecycleError):
    """A lifecycle hook exceeded its timeout."""
