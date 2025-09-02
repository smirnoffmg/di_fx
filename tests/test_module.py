"""Tests for Component functionality (formerly Module)."""

import pytest

from di_fx import Component, Invoke, Provide, Supply


class TestComponent:
    """Test the Component class and functionality."""

    def test_component_creation(self):
        """Test creating a component with components."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        def setup_routes() -> str:
            return "Routes"

        database_component = Component(
            Provide(create_database),
            Supply({"url": "localhost"}),
        )

        http_component = Component(
            Provide(create_server),
            Invoke(setup_routes),
        )

        assert len(database_component) == 2
        assert len(http_component) == 2

    def test_component_extraction(self):
        """Test that components properly extract their components."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        def setup_routes() -> str:
            return "Routes"

        database_component = Component(
            Provide(create_database),
            Supply({"url": "localhost"}),
        )

        http_component = Component(
            Provide(create_server),
            Invoke(setup_routes),
        )

        # Extract providers
        db_providers = database_component.get_providers()
        http_providers = http_component.get_providers()
        assert len(db_providers) == 1
        assert len(http_providers) == 1

        # Extract supplies
        db_supplies = database_component.get_supplies()
        http_supplies = http_component.get_supplies()
        assert len(db_supplies) == 1
        assert len(http_supplies) == 0

        # Extract invokables
        db_invokables = database_component.get_invokables()
        http_invokables = http_component.get_invokables()
        assert len(db_invokables) == 0
        assert len(http_invokables) == 1

    @pytest.mark.asyncio
    async def test_component_integration(self):
        """Test that components work correctly with the App."""

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

        database_component = Component(
            Provide(create_database),
            Invoke(seed_database),
        )

        http_component = Component(
            Provide(create_server),
            Invoke(setup_routes),
        )

        app = Component(database_component, http_component)

        async with app.lifecycle():
            # Not executed yet
            assert len(execution_order) == 0
            pass

        # After exiting context, both invoke functions should have been executed
        assert len(execution_order) == 2
        assert "setup_routes(Server)" in execution_order
        assert "seed_database(Database)" in execution_order

    def test_nested_components(self):
        """Test that components can contain other components."""

        def create_database() -> str:
            return "Database"

        def create_server() -> str:
            return "Server"

        inner_component = Component(Provide(create_database))
        outer_component = Component(inner_component, Provide(create_server))

        # Should extract components from nested components
        providers = outer_component.get_providers()
        assert len(providers) == 2  # One from inner, one from outer

        # Should be able to iterate over components
        components = list(outer_component)
        assert len(components) == 2
        assert isinstance(components[0], Component)
        assert isinstance(components[1], Provide)
