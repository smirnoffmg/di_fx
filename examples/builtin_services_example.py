"""
Built-in services example for di_fx.

This example demonstrates how to use the automatically provided
DotGraph and Shutdowner services.
"""

import asyncio
from typing import Annotated

from di_fx import Component, DotGraph, Invoke, Provide, Shutdowner

# Use Annotated types to create distinct types
DatabaseType = Annotated[str, "database"]
ServerType = Annotated[str, "server"]
ConfigType = Annotated[dict, "config"]


def create_database_config() -> ConfigType:
    """Create database configuration."""
    return {"url": "postgresql://localhost/mydb", "pool_size": 10}


def create_database(config: ConfigType) -> DatabaseType:
    """Create database connection."""
    print(f"Connecting to database: {config['url']}")
    return "Database"


def create_server() -> ServerType:
    """Create HTTP server."""
    print("Creating HTTP server")
    return "Server"


def setup_routes(server: ServerType) -> str:
    """Setup HTTP routes."""
    print(f"Setting up routes for {server}")
    return "Routes configured"


def seed_database(database: DatabaseType) -> str:
    """Seed database with initial data."""
    print(f"Seeding {database} with initial data")
    return "Database seeded"


def print_dependency_graph(graph: DotGraph) -> str:
    """Print the dependency graph in DOT format.

    This function automatically receives a DotGraph instance.
    """
    print("=" * 60)
    print("DEPENDENCY GRAPH (DOT format)")
    print("=" * 60)
    print(graph.to_dot())
    print("=" * 60)

    # You can also save to a file for visualization with Graphviz
    with open("dependencies.dot", "w") as f:
        f.write(graph.to_dot())
    print("Graph saved to 'dependencies.dot'")

    return "Graph printed and saved"


def setup_health_monitoring(
    shutdowner: Shutdowner, database: DatabaseType, server: ServerType
) -> str:
    """Setup health monitoring with automatic shutdown capability.

    This function automatically receives a Shutdowner instance.
    """
    print(f"Setting up health monitoring for {database} and {server}")

    # Simulate a health check that might trigger shutdown
    async def health_check() -> None:
        # Simulate some health monitoring logic
        await asyncio.sleep(0.1)

        # Example: if health check fails, trigger shutdown
        # (In real apps, this would be based on actual health metrics)
        if False:  # Simulate health check failure
            await shutdowner.shutdown("Health check failed")  # type: ignore[unreachable]

    # In a real app, you'd schedule this health check
    print("Health monitoring setup complete")
    return "Health monitoring configured"


def print_startup_info(database: DatabaseType, server: ServerType) -> str:
    """Print startup information."""
    print(f"Application started with {database} and {server}")
    return "Startup info printed"


# Create modules for different concerns
DatabaseModule = Component(
    Provide(create_database_config, create_database),
    Invoke(seed_database),
)

HttpModule = Component(
    Provide(create_server),
    Invoke(setup_routes),
)


# Group all modules together
def create_app() -> Component:
    """Create application options."""
    return Component(
        DatabaseModule,
        HttpModule,
        Invoke(
            print_dependency_graph,  # DotGraph auto-injected
            setup_health_monitoring,  # Shutdowner auto-injected
            print_startup_info,
        ),
    )


async def main() -> None:
    """Main application function."""
    print("Starting di_fx application with built-in services...")

    # Create the application with all components
    app = Component(create_app())

    # Validate the dependency graph before starting
    try:
        print("Validating dependency graph...")
        app.validate()
        print("✅ Validation passed! All dependencies can be resolved.")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return

    # Use the application lifecycle
    async with app.lifecycle():
        print("Application is running...")

        # Resolve dependencies to verify they work
        database = await app.resolve(DatabaseType)
        server = await app.resolve(ServerType)
        config = await app.resolve(ConfigType)

        print(f"Resolved: {database}, {server}, {config}")

        # Simulate some work
        await asyncio.sleep(0.1)

    print("Application stopped!")


async def demonstrate_shutdowner() -> None:
    """Demonstrate the Shutdowner functionality."""
    print("\n" + "=" * 60)
    print("DEMONSTRATING SHUTDOWNER")
    print("=" * 60)

    def create_service() -> str:
        return "TestService"

    def test_shutdown_function(shutdowner: Shutdowner, service: str) -> str:
        """Function that demonstrates Shutdowner usage."""
        print(f"Service {service} has access to shutdowner: {shutdowner}")

        # In a real app, you might use this for:
        # - Health monitoring
        # - Error handling
        # - Graceful degradation
        # - Circuit breaker patterns

        return f"Shutdowner configured for {service}"

    app = Component(Provide(create_service), Invoke(test_shutdown_function))

    # Run briefly to show Shutdowner injection
    async with app.lifecycle():
        await asyncio.sleep(0.05)

    print("Shutdowner demonstration complete!")


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())

    # Demonstrate Shutdowner
    asyncio.run(demonstrate_shutdowner())

    print("\n" + "=" * 60)
    print("BUILT-IN SERVICES DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("Check 'dependencies.dot' file for the generated graph!")
    print("You can visualize it with Graphviz: dot -Tpng dependencies.dot -o graph.png")
