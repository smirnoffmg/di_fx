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

    def __init__(self, providers: dict[type[Any], Provider]) -> None:
        """Initialize the validation manager.

        Args:
            providers: Dictionary of type -> provider mappings to validate
        """
        self._providers = providers

    def validate(self) -> None:
        """Validate the dependency graph before starting the application.

        This checks for:
        - Missing dependencies
        - Circular dependencies

        Raises:
            ValidationError: If validation fails
        """
        validate_dependency_graph(self._providers)

    def get_provider_count(self) -> int:
        """Get the number of providers being validated."""
        return len(self._providers)

    def has_providers(self) -> bool:
        """Check if there are any providers to validate."""
        return bool(self._providers)
