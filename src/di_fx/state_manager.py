"""
Application state management for dependency injection framework.

This module provides the StateManager class that handles all application state
concerns, including initialization status, running state, and component tracking.
"""

from typing import Any


class StateManager:
    """Manages the application state and provides state-related operations."""

    def __init__(self) -> None:
        """Initialize the state manager."""
        self._is_initialized = False
        self._is_running = False
        self._providers: dict[type[Any], Any] = {}
        self._values: dict[type[Any], Any] = {}
        self._invokables: list[Any] = []

    def set_components(
        self,
        providers: dict[type[Any], Any],
        values: dict[type[Any], Any],
        invokables: list[Any],
    ) -> None:
        """Set the application components."""
        self._providers = providers
        self._values = values
        self._invokables = invokables

    def mark_initialized(self) -> None:
        """Mark the application as initialized."""
        self._is_initialized = True

    def mark_running(self) -> None:
        """Mark the application as running."""
        self._is_running = True

    def mark_stopped(self) -> None:
        """Mark the application as stopped."""
        self._is_running = False

    def is_initialized(self) -> bool:
        """Check if the application has been initialized."""
        return self._is_initialized

    def is_running(self) -> bool:
        """Check if the application is currently running."""
        return self._is_running

    def has_provider(self, type_: type[Any]) -> bool:
        """Check if a provider exists for a type."""
        return type_ in self._providers

    def has_value(self, type_: type[Any]) -> bool:
        """Check if a value exists for a type."""
        return type_ in self._values

    def get_providers(self) -> dict[type[Any], Any]:
        """Get the processed providers."""
        return self._providers.copy()

    def get_values(self) -> dict[type[Any], Any]:
        """Get the processed values."""
        return self._values.copy()

    def get_invokables(self) -> list[Any]:
        """Get the processed invokables."""
        return self._invokables.copy()

    def get_component_counts(self) -> dict[str, int]:
        """Get counts of different component types."""
        return {
            "providers": len(self._providers),
            "values": len(self._values),
            "invokables": len(self._invokables),
        }

    def get_total_component_count(self) -> int:
        """Get the total number of components."""
        return len(self._providers) + len(self._values)

    def get_state_summary(self) -> dict[str, Any]:
        """Get a comprehensive summary of the application state."""
        return {
            "is_initialized": self._is_initialized,
            "is_running": self._is_running,
            "component_counts": self.get_component_counts(),
            "total_components": self.get_total_component_count(),
        }

    def reset(self) -> None:
        """Reset all state (useful for testing)."""
        self._is_initialized = False
        self._is_running = False
        self._providers.clear()
        self._values.clear()
        self._invokables.clear()

    def can_start(self) -> bool:
        """Check if the application can be started."""
        return self._is_initialized and not self._is_running

    def can_stop(self) -> bool:
        """Check if the application can be stopped."""
        return self._is_running

    def can_validate(self) -> bool:
        """Check if the application can be validated."""
        return not self._is_initialized and not self._is_running
