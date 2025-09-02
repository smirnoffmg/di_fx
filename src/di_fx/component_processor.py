"""
Shared component processing utilities for dependency injection framework.

This module provides a ComponentProcessor class that handles the extraction
of providers, supplies, and invokables from various component types.
"""

from typing import Any


class ComponentProcessor:
    """Shared utilities for processing DI components."""

    @staticmethod
    def extract_providers(components: tuple[Any, ...]) -> list[Any]:
        """Extract all Provide components from a collection of components."""
        providers = []
        for component in components:
            if hasattr(component, "get_providers"):
                providers.extend(component.get_providers())
            elif (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Provide"
            ):
                providers.append(component)
        return providers

    @staticmethod
    def extract_supplies(components: tuple[Any, ...]) -> list[Any]:
        """Extract all Supply components from a collection of components."""
        supplies = []
        for component in components:
            if hasattr(component, "get_supplies"):
                supplies.extend(component.get_supplies())
            elif (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Supply"
            ):
                supplies.append(component)
        return supplies

    @staticmethod
    def extract_invokables(components: tuple[Any, ...]) -> list[Any]:
        """Extract all Invokable components from a collection of components."""
        invokables = []
        for component in components:
            if hasattr(component, "get_invokables"):
                invokables.extend(component.get_invokables())
            elif (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Invoke"
            ):
                invokables.extend(component.get_invokables())
        return invokables

    @staticmethod
    def extract_all_components(components: tuple[Any, ...]) -> dict[str, list[Any]]:
        """Extract all component types from a collection of components."""
        return {
            "providers": ComponentProcessor.extract_providers(components),
            "supplies": ComponentProcessor.extract_supplies(components),
            "invokables": ComponentProcessor.extract_invokables(components),
        }
