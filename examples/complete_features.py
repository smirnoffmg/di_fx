"""
Complete features example for di_fx.

This example demonstrates all the new functionality:
- Invoke for startup initialization
- Module for named modular organization
- Component for grouping components
- Annotated types for distinct dependency injection
"""

import asyncio
from typing import Annotated

from di_fx import Component, Invoke, Provide

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
DatabaseModule = Component(
    "database",
    Provide(create_database_config, create_database),
    Invoke(seed_database),
)

HttpModule = Component(
    "http",
    Provide(create_server),
    Invoke(setup_routes),
)


# Group all modules together
def create_app() -> Component:
    """Create application options."""
    return Component(
        DatabaseModule,
        HttpModule,
        Invoke(print_startup_info),
    )


async def main() -> None:
    """Main application function."""
    print("Starting di_fx application with all features...")

    # Create the application with all components
    app = Component(create_app())

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


if __name__ == "__main__":
    asyncio.run(main())
