"""Tests for validation functionality."""

import pytest

from di_fx import Component, Invoke, Provide, ValidationError


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
