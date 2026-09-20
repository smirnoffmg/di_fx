"""Tests for built-in services (DotGraph and Shutdowner)."""

import pytest

from di_fx import App, DotGraph, Invoke, Provide, Shutdowner


class TestDotGraph:
    """Test the DotGraph built-in service."""

    @pytest.mark.asyncio
    async def test_dotgraph_auto_injection(self):
        """Test that DotGraph is automatically provided."""

        def create_config() -> dict:
            return {"port": 8000}

        def create_server(config: dict) -> str:
            return f"Server on port {config['port']}"

        def print_dependency_graph(graph: DotGraph) -> str:
            """Function that requests DotGraph - should be auto-injected."""
            dot_output = graph.to_dot()
            assert "digraph DependencyGraph" in dot_output
            assert "dict" in dot_output
            assert "str" in dot_output
            return dot_output

        app = App(Provide(create_config, create_server), Invoke(print_dependency_graph))

        # Should not raise any errors
        app.validate()

        # Run the app to trigger the DotGraph injection
        async with app.lifecycle():
            # The DotGraph should be automatically injected
            pass

    def test_dotgraph_creation(self):
        """Test creating DotGraph manually."""
        providers = {}
        values = {}

        graph = DotGraph(providers, values)
        assert isinstance(graph, DotGraph)
        assert graph.to_dot().startswith("digraph DependencyGraph")

    def test_dotgraph_with_dependencies(self):
        """Test DotGraph with actual dependencies."""

        # Mock provider with dependencies
        class MockProvider:
            def __init__(self, return_type, dependencies):
                self.return_type = return_type
                self.dependencies = dependencies

        providers = {str: MockProvider(str, [dict]), dict: MockProvider(dict, [])}
        values = {}

        graph = DotGraph(providers, values)
        dot_output = graph.to_dot()

        assert "dict" in dot_output
        assert "str" in dot_output
        # Check that the dependency edge exists (with proper DOT formatting)
        assert '"dict" -> "str"' in dot_output  # Dependency edge


class TestShutdowner:
    """Test the Shutdowner built-in service."""

    @pytest.mark.asyncio
    async def test_shutdowner_auto_injection(self):
        """Test that Shutdowner is automatically provided."""

        def create_service() -> str:
            return "Service"

        def setup_health_monitor(shutdowner: Shutdowner, service: str) -> str:
            """Function that requests Shutdowner - should be auto-injected."""
            assert isinstance(shutdowner, Shutdowner)
            assert not shutdowner.is_shutdown_requested()
            return f"Health monitor setup for {service}"

        app = App(Provide(create_service), Invoke(setup_health_monitor))

        # Should not raise any errors
        app.validate()

        # Run the app to trigger the Shutdowner injection
        async with app.lifecycle():
            # The Shutdowner should be automatically injected
            pass

    @pytest.mark.asyncio
    async def test_shutdowner_creation(self):
        """Test creating Shutdowner manually."""
        shutdown_called = False

        def shutdown_callback():
            nonlocal shutdown_called
            shutdown_called = True

        shutdowner = Shutdowner(shutdown_callback)
        assert isinstance(shutdowner, Shutdowner)
        assert not shutdowner.is_shutdown_requested()

        # Test shutdown (async)
        await shutdowner.shutdown("Test reason")
        assert shutdowner.is_shutdown_requested()
        assert shutdown_called

    @pytest.mark.asyncio
    async def test_shutdowner_async_shutdown(self):
        """Test async shutdown method."""
        shutdown_called = False

        def shutdown_callback():
            nonlocal shutdown_called
            shutdown_called = True

        shutdowner = Shutdowner(shutdown_callback)

        # Test async shutdown
        await shutdowner.shutdown("Async shutdown")
        assert shutdowner.is_shutdown_requested()
        assert shutdown_called

    @pytest.mark.asyncio
    async def test_shutdowner_multiple_shutdown_calls(self):
        """Test that multiple shutdown calls don't cause issues."""
        shutdown_count = 0

        def shutdown_callback():
            nonlocal shutdown_count
            shutdown_count += 1

        shutdowner = Shutdowner(shutdown_callback)

        # First shutdown (async)
        await shutdowner.shutdown("First")
        assert shutdown_count == 1

        # Second shutdown should not trigger callback again
        await shutdowner.shutdown("Second")
        assert shutdown_count == 1  # Still 1, not 2


class TestBuiltinServicesIntegration:
    """Test integration of built-in services with the full framework."""

    @pytest.mark.asyncio
    async def test_both_services_in_same_function(self):
        """Test that both DotGraph and Shutdowner can be injected together."""

        def create_service() -> str:
            return "Service"

        def setup_monitoring(
            graph: DotGraph, shutdowner: Shutdowner, service: str
        ) -> str:
            """Function that requests both built-in services."""
            # Verify DotGraph
            assert isinstance(graph, DotGraph)
            dot_output = graph.to_dot()
            assert "digraph DependencyGraph" in dot_output

            # Verify Shutdowner
            assert isinstance(shutdowner, Shutdowner)
            assert not shutdowner.is_shutdown_requested()

            return f"Monitoring setup for {service} with graph and shutdowner"

        app = App(Provide(create_service), Invoke(setup_monitoring))

        # Should not raise any errors
        app.validate()

        # Run the app
        async with app.lifecycle():
            pass
