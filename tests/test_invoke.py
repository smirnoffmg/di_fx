"""Tests for Invoke functionality."""

import pytest

from di_fx import Component, Invoke, Provide


class TestInvoke:
    """Test the Invoke class and functionality."""

    def test_invoke_creation(self):
        """Test creating an Invoke with functions."""

        def setup_routes():
            return "Routes setup"

        def seed_database():
            return "Database seeded"

        invoke = Invoke(setup_routes, seed_database)

        assert len(invoke) == 2
        assert len(invoke.get_invokables()) == 2

    def test_invoke_with_dependencies(self):
        """Test Invoke with functions that have dependencies."""

        def setup_routes(server: str):
            return f"Routes setup for {server}"

        def seed_database(config: dict):
            return f"Database seeded with {config}"

        invoke = Invoke(setup_routes, seed_database)

        invokables = invoke.get_invokables()
        assert len(invokables) == 2

        # Check dependencies are extracted
        setup_routes_invokable = next(i for i in invokables if i.name == "setup_routes")
        assert str in setup_routes_invokable.dependencies

        seed_db_invokable = next(i for i in invokables if i.name == "seed_database")
        assert dict in seed_db_invokable.dependencies

    @pytest.mark.asyncio
    async def test_invoke_execution(self):
        """Test that invokable functions are executed during app startup."""

        execution_order = []

        def create_server() -> str:
            return "HTTP Server"

        def create_config() -> dict:
            return {"port": 8000}

        def setup_routes(server: str, config: dict):
            execution_order.append(f"setup_routes({server}, {config})")
            return "Routes configured"

        def seed_database(config: dict):
            execution_order.append(f"seed_database({config})")
            return "Database seeded"

        app = Component(
            Provide(create_server, create_config),
            Invoke(setup_routes, seed_database),
        )

        # The invokable functions should have been executed during startup
        # They execute when the context manager exits and start() is called
        assert len(execution_order) == 0  # Not executed yet

        async with app.lifecycle():
            # Still not executed yet - they execute when start() is called
            assert len(execution_order) == 0
            pass

        # After exiting the context, invoke functions should have been executed
        assert len(execution_order) == 2
        assert "setup_routes(HTTP Server, {'port': 8000})" in execution_order
        assert "seed_database({'port': 8000})" in execution_order

    @pytest.mark.asyncio
    async def test_invoke_with_async_functions(self):
        """Test Invoke with async functions."""

        execution_order = []

        async def create_server() -> str:
            return "Async HTTP Server"

        def create_config() -> dict:
            return {"port": 8000}

        async def setup_routes(server: str, config: dict):
            execution_order.append(f"setup_routes({server}, {config})")
            return "Routes configured"

        async def seed_database(config: dict):
            execution_order.append(f"seed_database({config})")
            return "Database seeded"

        app = Component(
            Provide(create_server, create_config),
            Invoke(setup_routes, seed_database),
        )

        async with app.lifecycle():
            # Still not executed yet - they execute when start() is called
            assert len(execution_order) == 0
            pass

        # After exiting the context, invoke functions should have been executed
        assert len(execution_order) == 2
        assert "setup_routes(Async HTTP Server, {'port': 8000})" in execution_order
        assert "seed_database({'port': 8000})" in execution_order

    @pytest.mark.asyncio
    async def test_invoke_error_handling(self):
        """Test that errors in invokable functions are properly handled."""

        def create_server() -> str:
            return "HTTP Server"

        def failing_function(server: str):
            raise RuntimeError("Invoke function failed")

        app = Component(
            Provide(create_server),
            Invoke(failing_function),
        )

        # Should raise the error from the failing invokable function
        with pytest.raises(RuntimeError, match="Invoke function failed"):
            async with app.lifecycle():
                pass
