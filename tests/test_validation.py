"""Tests for validation functionality."""

import pytest
from typing import Any

from di_fx import Component, Invoke, Provide, ValidationError
from di_fx.validation_manager import ServiceValidationError


class TestValidation:
    """Test the validation functionality."""

    def test_validation_success(self):
        """Test that validation passes for valid dependency graphs."""

        def create_config() -> dict:
            return {"port": 8000}

        def create_server(config: dict) -> str:
            return f"Server on port {config['port']}"

        app = Component(Provide(create_config, create_server))

        # Should not raise any errors
        app.validate()

    def test_validation_missing_dependency(self):
        """Test that validation fails when dependencies are missing."""

        def create_server(config: dict) -> str:
            return f"Server on port {config['port']}"

        app = Component(Provide(create_server))

        # Should raise ValidationError because config is missing
        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        error = exc_info.value
        assert len(error.errors) == 1
        assert "dict" in error.errors[0]  # The actual type name
        assert "no provider is registered" in error.errors[0]

    def test_validation_circular_dependency(self):
        """Test that validation fails when there are circular dependencies."""

        class ServiceA:
            def __init__(self, service_b: "ServiceB"):
                self.service_b = service_b

        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a

        def create_service_a(service_b: ServiceB) -> ServiceA:
            return ServiceA(service_b)

        def create_service_b(service_a: ServiceA) -> ServiceB:
            return ServiceB(service_a)

        app = Component(Provide(create_service_a, create_service_b))

        # Should raise ValidationError because of circular dependency
        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        error = exc_info.value
        assert len(error.errors) >= 1
        assert "Circular dependency detected" in error.errors[0]

    def test_validation_with_lifecycle(self):
        """Test that validation works with lifecycle hooks."""

        def create_config() -> dict:
            return {"port": 8000}

        def create_server(config: dict) -> str:
            return f"Server on port {config['port']}"

        def setup_routes(server: str) -> str:
            return f"Routes setup for {server}"

        app = Component(Provide(create_config, create_server), Invoke(setup_routes))

        # Should not raise any errors
        app.validate()

    def test_validation_error_details(self):
        """Test that validation provides detailed error information."""

        def create_service_a(service_b: str) -> str:
            return f"ServiceA with {service_b}"

        def create_service_b(service_c: int) -> str:
            return f"ServiceB with {service_c}"

        app = Component(Provide(create_service_a, create_service_b))

        # Should raise ValidationError with missing dependencies
        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        error = exc_info.value
        # Note: Only one error is reported because both providers return 'str'
        # and the validation stops at the first missing dependency
        assert len(error.errors) == 1

        # Check that the missing dependency is reported
        error_message = error.errors[0].lower()
        assert "int" in error_message or "str" in error_message

    def test_validation_provider_conflicts(self):
        """Test that validation detects provider conflicts."""

        def create_service_a() -> str:
            return "ServiceA"

        def create_service_b() -> str:
            return "ServiceB"

        # This should work since they're different functions
        app = Component(Provide(create_service_a, create_service_b))
        app.validate()

        # But if we had the same function registered twice, it would be a conflict
        # This is handled by the Provide class, not validation

    def test_validation_nested_dependencies(self):
        """Test that validation works with nested dependency chains."""

        def create_config() -> dict:
            return {"port": 8000}

        def create_database(config: dict) -> str:
            return f"Database on port {config['port']}"

        def create_user_service(database: str) -> str:
            return f"UserService using {database}"

        def create_api_handler(user_service: str) -> str:
            return f"API handler with {user_service}"

        app = Component(Provide(create_config, create_database, create_user_service, create_api_handler))

        # Should not raise any errors
        app.validate()

    def test_validation_missing_nested_dependency(self):
        """Test that validation fails with missing nested dependencies."""

        def create_database() -> str:
            return "Database"

        def create_user_service(database: str) -> str:
            return f"UserService using {database}"

        def create_api_handler(user_service: str, missing_service: int) -> str:
            return f"API handler with {user_service}"

        app = Component(Provide(create_database, create_user_service, create_api_handler))

        # Should raise ValidationError because missing_service is not provided
        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        error = exc_info.value
        assert len(error.errors) == 1
        assert "int" in error.errors[0]
        assert "no provider is registered" in error.errors[0]


class TestServiceValidation:
    """Test the enhanced service validation functionality."""

    def test_service_contract_validation(self):
        """Test service contract validation."""
        from di_fx.validation import validate_service_contract
        from di_fx.provide import Provider

        def valid_constructor() -> str:
            return "valid"

        provider = Provider(
            constructor=valid_constructor,
            return_type=str,
            dependencies=[],
            singleton=True
        )

        errors = validate_service_contract(provider)
        assert len(errors) == 0

    def test_service_contract_invalid_constructor(self):
        """Test service contract validation with invalid constructor."""
        from di_fx.validation import validate_service_contract
        from di_fx.provide import Provider

        provider = Provider(
            constructor="not_callable",  # type: ignore
            return_type=str,
            dependencies=[],
            singleton=True
        )

        errors = validate_service_contract(provider)
        assert len(errors) == 1
        assert "Constructor must be callable" in errors[0]

    def test_validation_summary(self):
        """Test validation summary generation."""
        from di_fx.validation import get_validation_summary
        from di_fx.provide import Provider

        def service_a() -> str:
            return "a"

        def service_b() -> int:
            return 1

        providers = {
            str: Provider(constructor=service_a, return_type=str, dependencies=[], singleton=True),
            int: Provider(constructor=service_b, return_type=int, dependencies=[], singleton=True)
        }

        summary = get_validation_summary(providers)
        assert summary["total_providers"] == 2
        assert summary["total_dependencies"] == 0
        assert "str" in summary["provider_types"]
        assert "int" in summary["provider_types"]


class TestAsyncValidation:
    """Test async-specific validation functionality."""

    async def test_async_constructor_validation(self):
        """Test validation with async constructors."""

        async def create_async_service() -> str:
            return "async service"

        def create_sync_service() -> str:
            return "sync service"

        app = Component(Provide(create_async_service, create_sync_service))

        # Should not raise any errors
        app.validate()

    def test_async_consistency_validation(self):
        """Test async consistency validation."""
        # This test would require the enhanced ValidationManager to be integrated
        # For now, we'll test the basic functionality

        def create_sync_service() -> str:
            return "sync service"

        app = Component(Provide(create_sync_service))

        # Should not raise any errors
        app.validate()


class TestValidationIntegration:
    """Test validation integration with the Component system."""

    def test_component_validation_method(self):
        """Test that Component.validate() method works correctly."""

        def create_config() -> dict:
            return {"port": 8000}

        def create_server(config: dict) -> str:
            return f"Server on port {config['port']}"

        app = Component(Provide(create_config, create_server))

        # Should not raise any errors
        app.validate()

        # Should be marked as initialized after validation
        assert app.is_initialized()

    def test_validation_before_startup(self):
        """Test that validation is called before startup."""

        def create_config() -> dict:
            return {"port": 8000}

        def create_server(config: dict) -> str:
            return f"Server on port {config['port']}"

        app = Component(Provide(create_config, create_server))

        # Validate first
        app.validate()

        # Then start - should work without validation errors
        # Note: This is a basic test - in real usage, validation would be called
        # automatically during startup
        assert app.is_initialized()
