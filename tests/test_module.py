"""Tests for Module functionality."""

import pytest

from di_fx import App, Invoke, Module, Provide, Supply


class TestModule:
    """Test the Module class and functionality."""

    def test_module_creation(self):
        """Test creating a module with components."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        def setup_routes() -> str:
            return "Routes"

        database_module = Module(
            "database",
            Provide(create_database),
            Supply({"url": "localhost"}),
        )

        http_module = Module(
            "http",
            Provide(create_server),
            Invoke(setup_routes),
        )

        assert database_module.name == "database"
        assert http_module.name == "http"
        assert len(database_module) == 2
        assert len(http_module) == 2

    def test_module_component_extraction(self):
        """Test that modules properly extract their components."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        def setup_routes() -> str:
            return "Routes"

        database_module = Module(
            "database",
            Provide(create_database),
            Supply({"url": "localhost"}),
        )

        http_module = Module(
            "http",
            Provide(create_server),
            Invoke(setup_routes),
        )

        # Extract providers
        db_providers = database_module.get_providers()
        http_providers = http_module.get_providers()
        assert len(db_providers) == 1
        assert len(http_providers) == 1

        # Extract supplies
        db_supplies = database_module.get_supplies()
        http_supplies = http_module.get_supplies()
        assert len(db_supplies) == 1
        assert len(http_supplies) == 0

        # Extract invokables
        db_invokables = database_module.get_invokables()
        http_invokables = http_module.get_invokables()
        assert len(db_invokables) == 0
        assert len(http_invokables) == 1

    @pytest.mark.asyncio
    async def test_module_integration(self):
        """Test that modules work correctly with the App."""

        execution_order = []

        # Use Annotated types to create distinct types for dependency injection
        from typing import Annotated

        DatabaseType = Annotated[str, "database"]
        ServerType = Annotated[str, "server"]

        def create_database() -> DatabaseType:
            return "Database"

        def create_server() -> ServerType:
            return "Server"

        def setup_routes(server: ServerType):
            execution_order.append(f"setup_routes({server})")
            return "Routes configured"

        def seed_database(database: DatabaseType):
            execution_order.append(f"seed_database({database})")
            return "Database seeded"

        database_module = Module(
            "database",
            Provide(create_database),
            Invoke(seed_database),
        )

        http_module = Module(
            "http",
            Provide(create_server),
            Invoke(setup_routes),
        )

        app = App(database_module, http_module)

        async with app.lifecycle():
            # Not executed yet
            assert len(execution_order) == 0
            pass

        # After exiting context, both invoke functions should have been executed
        assert len(execution_order) == 2
        assert "setup_routes(Server)" in execution_order
        assert "seed_database(Database)" in execution_order

    def test_nested_modules(self):
        """Test that modules can contain other modules."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        inner_module = Module("inner", Provide(create_database))
        outer_module = Module("outer", inner_module, Provide(create_server))

        # Should extract components from nested modules
        providers = outer_module.get_providers()
        assert len(providers) == 2  # One from inner, one from outer

        # Should be able to iterate over components
        components = list(outer_module)
        assert len(components) == 2
        assert isinstance(components[0], Module)
        assert isinstance(components[1], Provide)
