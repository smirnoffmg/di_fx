"""
Module functionality for dependency injection framework.

This module provides the Module class for organizing related providers,
supplies, and invokables into named modules.
"""

from dataclasses import dataclass
from typing import Any

from .invoke import Invoke
from .provide import Provide
from .supply import Supply


@dataclass
class Module:
    """A named module containing related DI components."""

    name: str
    components: tuple[Any, ...]

    def __init__(self, name: str, *components: Any) -> None:
        self.name = name
        self.components = components

    def get_providers(self) -> list[Provide]:
        """Extract all Provide components from this module."""
        providers = []
        for component in self.components:
            if isinstance(component, Provide):
                providers.append(component)
            elif isinstance(component, Module):
                providers.extend(component.get_providers())
        return providers

    def get_supplies(self) -> list[Supply]:
        """Extract all Supply components from this module."""
        supplies = []
        for component in self.components:
            if isinstance(component, Supply):
                supplies.append(component)
            elif isinstance(component, Module):
                supplies.extend(component.get_supplies())
        return supplies

    def get_invokables(self) -> list[Any]:
        """Extract all Invokable components from this module."""
        invokables = []
        for component in self.components:
            if isinstance(component, Invoke):
                invokables.extend(component.get_invokables())
            elif isinstance(component, Module):
                invokables.extend(component.get_invokables())
        return invokables

    def __len__(self) -> int:
        return len(self.components)

    def __iter__(self) -> Any:
        return iter(self.components)
