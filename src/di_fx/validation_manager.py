"""
Validation management for dependency injection framework.

This module provides a ValidationManager class that handles all
validation logic, separating concerns from the main App class.
"""

import inspect
from typing import Any

from .provide import Provider
from .validation import ValidationError, validate_dependency_graph


class ServiceValidationError(ValidationError):
    """Raised when service validation fails."""

    def __init__(self, message: str, service_errors: list[tuple[type, list[str]]]) -> None:
        super().__init__(message, [])
        self.service_errors = service_errors


class ValidationManager:
    """Handles validation for the DI framework."""

    def __init__(self, providers: dict[type[Any], Provider]) -> None:
        """Initialize the validation manager.

        Args:
            providers: Dictionary of type -> provider mappings to validate
        """
        self._providers = providers
        self._validation_errors: list[str] = []

    def validate(self) -> None:
        """Validate the dependency graph before starting the application.

        This checks for:
        - Missing dependencies
        - Circular dependencies
        - Service contract validation
        - Constructor function validation

        Raises:
            ValidationError: If basic validation fails
            ServiceValidationError: If service validation fails
        """
        # First, run basic dependency graph validation
        try:
            validate_dependency_graph(self._providers)
        except ValidationError as e:
            self._validation_errors.extend(e.errors)
            raise

        # Then, run enhanced service validation
        service_errors = self._validate_services()
        if service_errors:
            raise ServiceValidationError(
                f"Service validation failed with {len(service_errors)} service(s) having issues:",
                service_errors
            )

    def _validate_services(self) -> list[tuple[type, list[str]]]:
        """Validate individual service contracts and constructors."""
        service_errors = []

        for service_type, provider in self._providers.items():
            errors = self._validate_service(service_type, provider)
            if errors:
                service_errors.append((service_type, errors))

        return service_errors

    def _validate_service(self, service_type: type, provider: Provider) -> list[str]:
        """Validate a single service contract."""
        errors = []

        # Validate constructor function
        constructor_errors = self._validate_constructor(provider.constructor)
        errors.extend(constructor_errors)

        # Validate return type annotation
        return_type_errors = self._validate_return_type(provider.constructor, service_type)
        errors.extend(return_type_errors)

        # Validate parameter annotations
        param_errors = self._validate_parameters(provider.constructor)
        errors.extend(param_errors)

        # Validate async consistency
        async_errors = self._validate_async_consistency(provider.constructor, service_type)
        errors.extend(async_errors)

        return errors

    def _validate_constructor(self, constructor: Any) -> list[str]:
        """Validate the constructor function."""
        errors = []

        if not callable(constructor):
            errors.append(f"Constructor must be callable, got {type(constructor).__name__}")
            return errors

        # Check if it's a coroutine function (async def)
        if inspect.iscoroutinefunction(constructor):
            # Async constructors are valid
            pass
        elif inspect.isfunction(constructor):
            # Regular functions are valid
            pass
        elif inspect.ismethod(constructor):
            # Methods are valid
            pass
        else:
            errors.append(f"Constructor must be a function or coroutine function, got {type(constructor).__name__}")

        return errors

    def _validate_return_type(self, constructor: Any, expected_type: type) -> list[str]:
        """Validate the return type annotation."""
        errors = []

        try:
            sig = inspect.signature(constructor)
            return_annotation = sig.return_annotation
        except (ValueError, TypeError):
            errors.append("Unable to inspect constructor signature")
            return errors

        if return_annotation == inspect.Signature.empty:
            errors.append("Constructor must have return type annotation")
            return errors

        # Check if the return type matches the expected type
        if return_annotation != expected_type:
            # Handle generic types like AsyncIterator[T]
            if hasattr(return_annotation, "__origin__") and return_annotation.__origin__ is not None:
                # This is a generic type, check if it's compatible
                if not self._is_generic_compatible(return_annotation, expected_type):
                    errors.append(
                        f"Return type {return_annotation} is not compatible with expected type {expected_type}"
                    )
            else:
                errors.append(
                    f"Return type {return_annotation} does not match expected type {expected_type}"
                )

        return errors

    def _validate_parameters(self, constructor: Any) -> list[str]:
        """Validate constructor parameters."""
        errors = []

        try:
            sig = inspect.signature(constructor)
        except (ValueError, TypeError):
            errors.append("Unable to inspect constructor signature")
            return errors

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = param.annotation
            if param_type == inspect.Signature.empty:
                errors.append(f"Parameter {param_name} must have type annotation")

            # Check for Any type usage (warn but don't fail)
            if param_type == Any:
                self._validation_errors.append(
                    f"Warning: Parameter {param_name} uses Any type - consider using specific types"
                )

        return errors

    def _validate_async_consistency(self, constructor: Any, service_type: type) -> list[str]:
        """Validate async consistency between constructor and service type."""
        errors = []

        is_async_constructor = inspect.iscoroutinefunction(constructor)

        # Check if the service type has async methods that suggest it should be async
        if hasattr(service_type, "__dict__"):
            has_async_methods = any(
                inspect.iscoroutinefunction(method)
                for method in service_type.__dict__.values()
                if callable(method)
            )

            if has_async_methods and not is_async_constructor:
                errors.append(
                    f"Service {service_type.__name__} has async methods but constructor is not async"
                )

        return errors

    def _is_generic_compatible(self, generic_type: type, expected_type: type) -> bool:
        """Check if a generic type is compatible with the expected type."""
        # Handle AsyncIterator[T] -> T case
        if (hasattr(generic_type, "__origin__") and
            generic_type.__origin__ is not None and
            hasattr(expected_type, "__origin__") and
            expected_type.__origin__ is not None):

            # Both are generics, check origin compatibility
            if generic_type.__origin__ == expected_type.__origin__:
                return True

            # Special case: AsyncIterator[T] can provide T
            if (generic_type.__origin__.__name__ == "AsyncIterator" and
                expected_type.__origin__ is None):
                return True

        return False

    def get_provider_count(self) -> int:
        """Get the number of providers being validated."""
        return len(self._providers)

    def has_providers(self) -> bool:
        """Check if there are any providers to validate."""
        return bool(self._providers)

    def get_validation_summary(self) -> dict[str, Any]:
        """Get a summary of validation results."""
        return {
            "total_providers": len(self._providers),
            "validation_errors": len(self._validation_errors),
            "provider_types": [t.__name__ for t in self._providers.keys()],
            "errors": self._validation_errors.copy()
        }

    def clear_validation_errors(self) -> None:
        """Clear accumulated validation errors."""
        self._validation_errors.clear()
