"""Tests for Component functionality."""

from di_fx import Component, Invoke, Provide, Supply


def create_database() -> str:
    """Create a database connection."""
    return "Database"


def create_server() -> str:
    """Create an HTTP server."""
    return "Server"


def create_config() -> dict:
    """Create configuration."""
    return {"port": 8000}


def setup_database(db: str) -> str:
    """Setup database."""
    return f"{db} setup complete"


def setup_server(server: str, config: dict) -> str:
    """Setup server."""
    return f"{server} setup complete on port {config['port']}"


class TestComponent(Component):
    """Concrete test implementation of Component for testing."""

    def get_providers(self) -> list:
        """Get providers from this test component and its sub-components."""
        providers = []
        for component in self._components:
            if hasattr(component, "get_providers"):
                providers.extend(component.get_providers())
            elif (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Provide"
            ):
                providers.append(component)
        return providers

    def get_supplies(self) -> list:
        """Get supplies from this test component and its sub-components."""
        supplies = []
        for component in self._components:
            if hasattr(component, "get_supplies"):
                supplies.extend(component.get_supplies())
            elif (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Supply"
            ):
                supplies.append(component)
        return supplies

    def get_invokables(self) -> list:
        """Get invokables from this test component and its sub-components."""
        invokables = []
        for component in self._components:
            if hasattr(component, "get_invokables"):
                invokables.extend(component.get_invokables())
            elif (
                hasattr(component, "__class__")
                and component.__class__.__name__ == "Invoke"
            ):
                invokables.extend(component.get_invokables())
        return invokables


class TestComponentClass:
    """Test the Component class and functionality."""

    def test_component_creation(self):
        """Test creating a component with sub-components."""
        # Create components for different concerns
        database_component = TestComponent(
            Provide(create_database),
            Supply(create_config()),
        )

        http_component = TestComponent(
            Provide(create_server),
            Invoke(setup_server),
        )

        # Test component creation
        assert len(database_component) == 2
        assert len(http_component) == 2

    def test_component_extraction(self):
        """Test that components properly extract their sub-components."""
        # Create components for different concerns
        database_component = TestComponent(
            Provide(create_database),
            Supply(create_config()),
        )

        http_component = TestComponent(
            Provide(create_server),
            Invoke(setup_server),
        )

        # Test component extraction
        db_providers = database_component.get_providers()
        http_providers = http_component.get_providers()

        assert len(db_providers) == 1
        assert len(http_providers) == 1

        db_supplies = database_component.get_supplies()
        http_supplies = http_component.get_supplies()

        assert len(db_supplies) == 1
        assert len(http_supplies) == 0

        db_invokables = database_component.get_invokables()
        http_invokables = http_component.get_invokables()

        assert len(db_invokables) == 0
        assert len(http_invokables) == 1

    def test_component_with_modules(self):
        """Test that Components can contain modules."""
        # Create modules for different concerns
        database_module = Component(
            Provide(create_database),
            Supply(create_config()),
        )

        http_module = Component(
            Provide(create_server),
            Invoke(setup_server),
        )

        # Create a component containing modules
        app_component = TestComponent(database_module, http_module)

        # Should extract components from modules
        providers = app_component.get_providers()
        supplies = app_component.get_supplies()
        invokables = app_component.get_invokables()

        assert len(providers) == 2  # One from each module
        assert len(supplies) == 1  # One from database module
        assert len(invokables) == 1  # One from http module

    def test_nested_components(self):
        """Test that components can contain other components."""
        # Create inner components
        inner_database = TestComponent(Provide(create_database))
        inner_server = TestComponent(Provide(create_server))

        # Create outer component containing inner components
        outer_component = TestComponent(inner_database, inner_server)

        # Should extract components from nested components
        providers = outer_component.get_providers()
        assert len(providers) == 2  # One from each inner component

        # Test iteration
        components = list(outer_component)
        assert len(components) == 2
        assert isinstance(components[0], TestComponent)
        assert isinstance(components[1], TestComponent)

    def test_component_integration(self):
        """Test that components work correctly with the App."""
        # Create components for different concerns
        database_component = TestComponent(
            Provide(create_database),
            Supply(create_config()),
        )

        http_component = TestComponent(
            Provide(create_server),
            Invoke(setup_server),
        )

        # Create app with components
        app = TestComponent(database_component, http_component)

        # Test that the app can process components
        assert len(app) == 2  # Two components
        assert app.has_provider(str)  # Should have string providers
        assert app.has_value(dict)  # Should have dict values

    def test_component_methods(self):
        """Test component utility methods."""
        # Create a component
        component = TestComponent(
            Provide(create_database),
            Supply(create_config()),
            Invoke(setup_database),
        )

        # Test component counts
        counts = component.get_component_counts()
        assert counts["providers"] == 1
        assert counts["supplies"] == 1
        assert counts["invokables"] == 1
        assert counts["components"] == 3
        assert counts["total"] == 3

        # Test flattening
        flattened = component.flatten()
        assert len(flattened) == 3

        # Test adding/removing components
        new_provider = Provide(create_server)
        component.add_component(new_provider)
        assert len(component) == 4

        component.remove_component(new_provider)
        assert len(component) == 3

        # Test clearing
        component.clear_components()
        assert len(component) == 0
