"""
Named parameters for dependency injection framework.

This module provides the Named class that allows multiple providers
of the same type by giving them distinct names.
"""

from typing import Any, TypeVar

T = TypeVar("T", bound=Any)


class Named:
    """A named type that can be used to distinguish between different instances of the same type.

    This allows multiple providers of the same type to coexist by giving them different names.
    Similar to Uber-Fx's fx.Named.

    Example:
        PrimaryDB = Named("primary", Database)
        ReplicaDB = Named("replica", Database)

        def create_primary() -> PrimaryDB: ...
        def create_replica() -> ReplicaDB: ...
    """

    def __init__(self, name: str, type_: type[T]) -> None:
        """Initialize a named type.

        Args:
            name: The name identifier for this type
            type_: The base type being named
        """
        self.name = name
        self.type = type_

    def __repr__(self) -> str:
        """String representation."""
        return f"Named({self.name!r}, {self.type.__name__})"

    def __eq__(self, other: Any) -> bool:
        """Equality comparison."""
        if not isinstance(other, Named):
            return False
        return self.name == other.name and self.type == other.type

    def __hash__(self) -> int:
        """Hash for use in sets and dicts."""
        return hash((self.name, self.type))


def is_named_type(type_: type[Any]) -> bool:
    """Check if a type is a Named type.

    Args:
        type_: The type to check

    Returns:
        True if the type is a Named type
    """
    return isinstance(type_, Named)


def get_named_type_info(type_: type[Any]) -> tuple[str, type[Any]] | None:
    """Get the name and base type from a Named type.

    Args:
        type_: The type to extract info from

    Returns:
        Tuple of (name, base_type) if it's a Named type, None otherwise
    """
    if isinstance(type_, Named):
        return type_.name, type_.type
    return None
