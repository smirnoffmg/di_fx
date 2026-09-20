"""
Validation management for dependency injection framework.

This module provides a ValidationManager class that handles all
validation logic, separating concerns from the main App class.
"""

from typing import Any

from .provide import Provider
from .validation import validate_dependency_graph


class ValidationManager:
    """Handles validation for the DI framework."""

    def __init__(
        self,
        providers: dict[type[Any], Provider],
        values: dict[type[Any], Any] | None = None,
        invokables: list[Any] | None = None,
    ) -> None:
        """Initialize the validation manager.

        Args:
            providers: Dictionary of type -> provider mappings to validate
            values: Dictionary of type -> supplied value mappings
            invokables: Functions that will run at startup
        """
        self._providers = providers
        self._values = values or {}
        self._invokables = invokables or []

    def validate(self) -> None:
        """Validate the dependency graph before starting the application.

        This checks for:
        - Missing dependencies, for providers and invokables alike
        - Circular dependencies

        Raises:
            ValidationError: If validation fails
        """
        validate_dependency_graph(self._providers, self._values, self._invokables)

    def get_provider_count(self) -> int:
        """Get the number of providers being validated."""
        return len(self._providers)

    def has_providers(self) -> bool:
        """Check if there are any providers to validate."""
        return bool(self._providers)
