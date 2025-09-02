"""Tests for Options functionality."""

import pytest

from di_fx import App, Invoke, Module, Options, Provide, Supply


class TestOptions:
    """Test the Options class and functionality."""

    def test_options_creation(self):
        """Test creating Options with components."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        def setup_routes() -> str:
            return "Routes"

        options = Options(
            Provide(create_database, create_server),
            Invoke(setup_routes),
            Supply({"port": 8000}),
        )

        assert len(options) == 3

    def test_options_component_extraction(self):
        """Test that Options properly extract their components."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        def setup_routes() -> str:
            return "Routes"

        options = Options(
            Provide(create_database, create_server),
            Invoke(setup_routes),
            Supply({"port": 8000}),
        )

        # Extract providers
        providers = options.get_providers()
        assert len(providers) == 1  # One Provide container with 2 functions

        # Extract supplies
        supplies = options.get_supplies()
        assert len(supplies) == 1  # One Supply container

        # Extract invokables
        invokables = options.get_invokables()
        assert len(invokables) == 1  # One Invoke container

    def test_options_with_modules(self):
        """Test that Options can contain modules."""

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

        options = Options(database_module, http_module)

        # Should extract components from modules
        providers = options.get_providers()
        supplies = options.get_supplies()
        invokables = options.get_invokables()

        assert len(providers) == 2  # One from each module
        assert len(supplies) == 1  # One from database module
        assert len(invokables) == 1  # One from http module

    def test_nested_options(self):
        """Test that Options can contain other Options."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        inner_options = Options(Provide(create_database))
        outer_options = Options(inner_options, Provide(create_server))

        # Should extract components from nested options
        providers = outer_options.get_providers()
        assert len(providers) == 2  # One from inner, one from outer

    @pytest.mark.asyncio
    async def test_options_integration(self):
        """Test that Options work correctly with the App."""

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

        app_options = Options(database_module, http_module)
        app = App(app_options)

        async with app.lifecycle():
            # Not executed yet
            assert len(execution_order) == 0
            pass

        # After exiting context, both invoke functions should have been executed
        assert len(execution_order) == 2
        assert "setup_routes(Server)" in execution_order
        assert "seed_database(Database)" in execution_order

    def test_options_iteration(self):
        """Test that Options can be iterated over."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        options = Options(
            Provide(create_database),
            Supply({"port": 8000}),
            Invoke(create_server),
        )

        components = list(options)
        assert len(components) == 3
        assert isinstance(components[0], Provide)
        assert isinstance(components[1], Supply)
        assert isinstance(components[2], Invoke)
