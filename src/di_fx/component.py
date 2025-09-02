"""
Universal component system for dependency injection framework.

This module provides the Component class that serves as the foundation
for all DI components, allowing recursive component containment and
unified component processing. Component is now the main application container.
"""

import asyncio
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Any, TypeVar

T = TypeVar("T", bound=Any)


class Component:
    """Base class for all DI components with recursive containment support.

    Component is now the main application container that provides all the
    functionality previously available in the App class.
    """

    def __init__(self, *components: Any) -> None:
        """Initialize a component with optional sub-components."""
        self._components = list(components)

        # Initialize the orchestrator for application functionality
        # Use lazy import to avoid circular dependency
        from .app_orchestrator import AppOrchestrator

        self._orchestrator = AppOrchestrator(*components)

    def get_providers(self) -> list[Any]:
        """Extract all Provide components from this component."""
        # Default implementation: extract from _components
        providers = []
        for component in self._components:
            if (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Provide"
            ):
                providers.append(component)
            elif isinstance(component, Component):
                providers.extend(component.get_providers())
        return providers

    def get_supplies(self) -> list[Any]:
        """Extract all Supply components from this component."""
        # Default implementation: extract from _components
        supplies = []
        for component in self._components:
            if (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Supply"
            ):
                supplies.append(component)
            elif isinstance(component, Component):
                supplies.extend(component.get_supplies())
        return supplies

    def get_invokables(self) -> list[Any]:
        """Extract all Invokable components from this component."""
        # Default implementation: extract from _components
        invokables = []
        for component in self._components:
            if (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Invoke"
            ):
                invokables.append(component)
            elif isinstance(component, Component):
                invokables.extend(component.get_invokables())
        return invokables

    def get_components(self) -> list[Any]:
        """Get all sub-components contained within this component."""
        return self._components.copy()

    def add_component(self, component: Any) -> None:
        """Add a component to this component."""
        self._components.append(component)

    def remove_component(self, component: Any) -> None:
        """Remove a component from this component."""
        if component in self._components:
            self._components.remove(component)

    def clear_components(self) -> None:
        """Clear all sub-components from this component."""
        self._components.clear()

    def __len__(self) -> int:
        """Get the total number of components (including sub-components)."""
        return len(self._components)

    def __iter__(self) -> Iterator[Any]:
        """Iterate over all sub-components."""
        return iter(self._components)

    def flatten(self) -> list[Any]:
        """Flatten the component hierarchy into a single list."""
        components = []
        for component in self._components:
            # Always add the component itself
            components.append(component)
            # If it's a Component, also add its flattened sub-components
            if isinstance(component, Component):
                components.extend(component.flatten())
        return components

    def get_component_counts(self) -> dict[str, int]:
        """Get counts of different component types."""
        providers = self.get_providers()
        supplies = self.get_supplies()
        invokables = self.get_invokables()

        return {
            "providers": len(providers),
            "supplies": len(supplies),
            "invokables": len(invokables),
            "components": len(self._components),
            "total": len(providers) + len(supplies) + len(invokables),
        }

    def extract_nested_components(self, component_type: str) -> list[Any]:
        """Extract components of a specific type from nested components.

        Args:
            component_type: The type of component to extract ('providers', 'supplies', 'invokables')

        Returns:
            List of extracted components
        """
        extracted = []

        # Extract from this component
        if component_type == "providers":
            extracted.extend(self.get_providers())
        elif component_type == "supplies":
            extracted.extend(self.get_supplies())
        elif component_type == "invokables":
            extracted.extend(self.get_invokables())

        # Recursively extract from nested components
        for component in self._components:
            if isinstance(component, Component):
                extracted.extend(component.extract_nested_components(component_type))

        return extracted

    # Application container methods (previously in App class)

    async def resolve(self, type_: type[T]) -> Any:
        """Resolve a dependency of the specified type."""
        return await self._orchestrator.resolve(type_)

    async def start(self) -> None:
        """Start the application lifecycle."""
        await self._orchestrator.start()

    async def stop(self) -> None:
        """Stop the application lifecycle and cleanup resources."""
        await self._orchestrator.stop()

    def create_task(self, coro: Any) -> asyncio.Task[Any]:
        """Create and track an asyncio task."""
        return self._orchestrator.create_task(coro)

    @asynccontextmanager
    async def lifecycle(self) -> Any:
        """Context manager for application lifecycle."""
        try:
            # Don't start lifecycle yet - let dependencies resolve first
            yield self
            # Start the application after dependencies are resolved
            await self.start()
        finally:
            if self._orchestrator.is_running():
                await self.stop()

    async def run(self) -> None:
        """Run the application with proper asyncio event loop integration."""
        await self._orchestrator.run()

    def has_provider(self, type_: type[T]) -> bool:
        """Check if a provider exists for a type."""
        return self._orchestrator.has_provider(type_)

    def has_value(self, type_: type[T]) -> bool:
        """Check if a value exists for a type."""
        return self._orchestrator.has_value(type_)

    def validate(self) -> None:
        """Validate the dependency graph before starting the application."""
        self._orchestrator.validate()

    def is_running(self) -> bool:
        """Check if the application is currently running."""
        return self._orchestrator.is_running()

    def is_initialized(self) -> bool:
        """Check if the application has been initialized."""
        return self._orchestrator.is_initialized()

    def get_orchestrator_component_counts(self) -> dict[str, int]:
        """Get counts of different component types from the orchestrator."""
        return self._orchestrator.get_component_counts()
