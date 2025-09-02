"""
Validation example for di_fx.

This example demonstrates how to validate dependency graphs
before starting the application to catch missing dependencies.
"""

import asyncio
from typing import Annotated

from di_fx import App, Invoke, Module, Options, Provide, ValidationError

# Use Annotated types to create distinct types for dependency injection
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


def print_startup_info(database: DatabaseType, server: ServerType) -> str:
    """Print startup information."""
    print(f"Application started with {database} and {server}")
    return "Startup info printed"


# Create modules for different concerns
DatabaseModule = Module(
    "database",
    Provide(create_database_config, create_database),
    Invoke(seed_database),
)

HttpModule = Module(
    "http",
    Provide(create_server),
    Invoke(setup_routes),
)


# Group all modules together
def create_app() -> Options:
    """Create application options."""
    return Options(
        DatabaseModule,
        HttpModule,
        Invoke(print_startup_info),
    )


async def main() -> None:
    """Main application function."""
    print("Starting di_fx application with validation...")

    # Create the application with all components
    app = App(create_app())

    # Validate the dependency graph before starting
    try:
        print("Validating dependency graph...")
        app.validate()
        print("✅ Validation passed! All dependencies can be resolved.")
    except ValidationError as e:
        print(f"❌ Validation failed: {e}")
        print("Errors:")
        for error in e.errors:
            print(f"  - {error}")
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


async def demonstrate_validation_failure() -> None:
    """Demonstrate what happens when validation fails."""
    print("\n" + "=" * 50)
    print("DEMONSTRATING VALIDATION FAILURE")
    print("=" * 50)

    # Create an app with missing dependencies
    def create_service_a(service_b: str) -> str:
        return f"ServiceA with {service_b}"

    def create_service_b(service_c: int) -> str:
        return f"ServiceB with {service_c}"

    app = App(Provide(create_service_a, create_service_b))

    try:
        print("Validating dependency graph with missing dependencies...")
        app.validate()
        print("❌ This should have failed!")
    except ValidationError as e:
        print(f"✅ Validation correctly failed: {e}")
        print("Errors:")
        for error in e.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    # Run the successful example
    asyncio.run(main())

    # Demonstrate validation failure
    asyncio.run(demonstrate_validation_failure())
