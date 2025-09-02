"""
Component processor manager for dependency injection framework.

This module provides the ComponentProcessorManager class that manages
component processing logic, separating concerns from the main Component class.
"""

from typing import Any

from .component import Component
from .component_processor import ComponentProcessor
from .invoke import Invoke
from .provide import Provide
from .supply import Supply


class ComponentProcessorManager:
    """Manages the processing of DI components during application initialization."""

    def __init__(self) -> None:
        """Initialize the component processor manager."""
        self._providers: dict[type[Any], Any] = {}
        self._values: dict[type[Any], Any] = {}
        self._invokables: list[Any] = []

    def process_component(self, component: Any) -> None:
        """Process a single component and extract its providers, values, and invokables.

        Args:
            component: The component to process (Provide, Supply, Invoke, or Component)
        """
        if isinstance(component, Provide):
            self._providers.update(
                {provider.return_type: provider for provider in component}
            )
        elif isinstance(component, Supply):
            self._values.update({value.type_: value for value in component})
        elif isinstance(component, Invoke):
            self._invokables.extend(component.get_invokables())
        elif isinstance(component, Component):
            # Extract components from Component using shared processor
            components_tuple = tuple(component.get_components())
            providers = ComponentProcessor.extract_providers(components_tuple)
            supplies = ComponentProcessor.extract_supplies(components_tuple)
            invokables = ComponentProcessor.extract_invokables(components_tuple)

            # Add extracted providers
            for provider in providers:
                self._providers[provider.return_type] = provider

            # Add extracted supplies
            for supply in supplies:
                self._values[supply.type_] = supply

            # Add extracted invokables
            self._invokables.extend(invokables)
        else:
            raise ValueError(f"Unknown component type: {type(component)}")

    def get_providers(self) -> dict[type[Any], Any]:
        """Get the processed providers."""
        return self._providers.copy()

    def get_values(self) -> dict[type[Any], Any]:
        """Get the processed values."""
        return self._values.copy()

    def get_invokables(self) -> list[Any]:
        """Get the processed invokables."""
        return self._invokables.copy()

    def get_provider_count(self) -> int:
        """Get the number of providers processed."""
        return len(self._providers)

    def get_value_count(self) -> int:
        """Get the number of values processed."""
        return len(self._values)

    def get_invokable_count(self) -> int:
        """Get the number of invokables processed."""
        return len(self._invokables)

    def has_components(self) -> bool:
        """Check if any components have been processed."""
        return bool(self._providers or self._values or self._invokables)

    def reset(self) -> None:
        """Reset all processed components (useful for testing)."""
        self._providers.clear()
        self._values.clear()
        self._invokables.clear()
