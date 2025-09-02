"""
Simple interface registration for dependency injection framework.

This module provides a simple way to register constructors under multiple
interface types, similar to Uber-Fx's fx.Annotate() and fx.As().
"""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T", bound=Any)


class As:
    """Mark a constructor as providing a specific interface type."""

    def __init__(self, interface_type: type[T]) -> None:
        self.interface_type = interface_type

    def __repr__(self) -> str:
        return f"As({self.interface_type.__name__})"


def Annotate(
    constructor: Callable[..., Any], *annotations: As
) -> tuple[Callable[..., Any], list[As]]:
    """Mark a constructor as providing multiple interface types.

    Returns a tuple of (constructor, annotations) that Provide can handle.

    Example:
        from di_fx import Annotate, As, Provide

        app = App(
            Provide(
                Annotate(new_user_repo, As(UserAccessor), As(UserStorage))
            )
        )
    """
    return constructor, list(annotations)


__all__ = ["Annotate", "As"]
