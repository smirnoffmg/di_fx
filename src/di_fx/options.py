"""
Options functionality for dependency injection framework.

This module provides the Options class for grouping DI components
together, similar to Uber-Fx's fx.Options().
"""

from typing import Any

from .invoke import Invoke
from .module import Module
from .provide import Provide
from .supply import Supply


class Options:
    """Container for grouping DI components together."""

    def __init__(self, *components: Any) -> None:
        self._components = components

    def get_providers(self) -> list[Provide]:
        """Extract all Provide components from these options."""
        providers = []
        for component in self._components:
            if isinstance(component, Provide):
                providers.append(component)
            elif isinstance(component, Module):
                providers.extend(component.get_providers())
            elif isinstance(component, Options):
                providers.extend(component.get_providers())
        return providers

    def get_supplies(self) -> list[Supply]:
        """Extract all Supply components from these options."""
        supplies = []
        for component in self._components:
            if isinstance(component, Supply):
                supplies.append(component)
            elif isinstance(component, Module):
                supplies.extend(component.get_supplies())
            elif isinstance(component, Options):
                supplies.extend(component.get_supplies())
        return supplies

    def get_invokables(self) -> list[Any]:
        """Extract all Invokable components from these options."""
        invokables = []
        for component in self._components:
            if isinstance(component, Invoke):
                invokables.extend(component.get_invokables())
            elif isinstance(component, Module):
                invokables.extend(component.get_invokables())
            elif isinstance(component, Options):
                invokables.extend(component.get_invokables())
        return invokables

    def __len__(self) -> int:
        return len(self._components)

    def __iter__(self) -> Any:
        return iter(self._components)
