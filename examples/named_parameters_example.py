"""
Named parameters example for di_fx.

This example demonstrates how to use Named parameters to have
multiple providers of the same type with different names.
"""

import asyncio
from typing import Annotated

from di_fx import App, Invoke, Module, Named, Options, Provide

# Use Annotated types to create distinct types
DatabaseType = Annotated[str, "database"]
ServerType = Annotated[str, "server"]


class Database:
    """Database connection class."""

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def __repr__(self) -> str:
        return f"Database({self.name}: {self.url})"


class Config:
    """Configuration class."""

    def __init__(self, source: str, data: dict):
        self.source = source
        self.data = data

    def __repr__(self) -> str:
        return f"Config({self.source}: {self.data})"


# Create named types for different database instances
PrimaryDB = Named("primary", Database)
ReplicaDB = Named("replica", Database)

# Create named types for different config sources
EnvConfig = Named("env", Config)
FileConfig = Named("file", Config)


def create_primary_database() -> PrimaryDB:
    """Create primary database connection."""
    print("Creating primary database connection...")
    return Database("primary", "postgresql://primary/db")


def create_replica_database() -> ReplicaDB:
    """Create replica database connection."""
    print("Creating replica database connection...")
    return Database("replica", "postgresql://replica/db")


def create_env_config() -> EnvConfig:
    """Create configuration from environment variables."""
    print("Loading configuration from environment...")
    return Config("environment", {"port": 8000, "host": "localhost"})


def create_file_config() -> FileConfig:
    """Create configuration from file."""
    print("Loading configuration from file...")
    return Config("file", {"debug": True, "log_level": "info"})


def create_server() -> ServerType:
    """Create HTTP server."""
    print("Creating HTTP server...")
    return "http://localhost:8000"


def setup_database_connections(primary_db: PrimaryDB, replica_db: ReplicaDB) -> str:
    """Setup database connections with named parameters.

    This function receives different Database instances based on their names.
    """
    print("Setting up database connections:")
    print(f"  Primary: {primary_db}")
    print(f"  Replica: {replica_db}")

    # In a real app, you might:
    # - Use primary for writes
    # - Use replica for reads
    # - Setup connection pooling
    # - Configure failover

    return f"Database connections setup: {primary_db.name}, {replica_db.name}"


def merge_configurations(env_config: EnvConfig, file_config: FileConfig) -> str:
    """Merge configurations from different sources.

    This function receives different Config instances based on their names.
    """
    print("Merging configurations:")
    print(f"  Environment: {env_config}")
    print(f"  File: {file_config}")

    # In a real app, you might:
    # - Merge configs with priority rules
    # - Validate configurations
    # - Apply defaults
    # - Handle conflicts

    merged = {**env_config.data, **file_config.data}
    return f"Config merged from {env_config.source} and {file_config.source}: {merged}"


def setup_services(
    primary_db: PrimaryDB,
    replica_db: ReplicaDB,
    env_config: EnvConfig,
    file_config: FileConfig,
    server: ServerType,
) -> str:
    """Setup all services with named parameters.

    This demonstrates how Named parameters work with multiple types.
    """
    print("Setting up all services:")
    print(f"  Server: {server}")
    print(f"  Primary DB: {primary_db}")
    print(f"  Replica DB: {replica_db}")
    print(f"  Env Config: {env_config}")
    print(f"  File Config: {file_config}")

    return "All services configured successfully"


# Create modules for different concerns
DatabaseModule = Module(
    "database",
    Provide(create_primary_database, create_replica_database),
    Invoke(setup_database_connections),
)

ConfigModule = Module(
    "config",
    Provide(create_env_config, create_file_config),
    Invoke(merge_configurations),
)

HttpModule = Module(
    "http",
    Provide(create_server),
)


# Group all modules together
def create_app() -> Options:
    """Create application options."""
    return Options(
        DatabaseModule,
        ConfigModule,
        HttpModule,
        Invoke(setup_services),
    )


async def main() -> None:
    """Main application function."""
    print("Starting di_fx application with Named parameters...")
    print("=" * 60)

    # Create the application with all components
    app = App(create_app())

    # Validate the dependency graph before starting
    try:
        print("Validating dependency graph...")
        app.validate()
        print("✅ Validation passed! All dependencies can be resolved.")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return

    print("\n" + "=" * 60)
    print("RUNNING APPLICATION")
    print("=" * 60)

    # Use the application lifecycle
    async with app.lifecycle():
        print("Application is running...")

        # Resolve dependencies to verify they work
        primary_db = await app.resolve(PrimaryDB)
        replica_db = await app.resolve(ReplicaDB)
        env_config = await app.resolve(EnvConfig)
        file_config = await app.resolve(FileConfig)
        server = await app.resolve(ServerType)

        print("\nResolved dependencies:")
        print(f"  Primary DB: {primary_db}")
        print(f"  Replica DB: {replica_db}")
        print(f"  Env Config: {env_config}")
        print(f"  File Config: {file_config}")
        print(f"  Server: {server}")

        # Simulate some work
        await asyncio.sleep(0.1)

    print("\nApplication stopped!")


async def demonstrate_named_benefits() -> None:
    """Demonstrate the benefits of Named parameters."""
    print("\n" + "=" * 60)
    print("DEMONSTRATING NAMED PARAMETERS BENEFITS")
    print("=" * 60)

    # Without Named parameters - PROBLEM: Can't have multiple Database providers
    print("❌ WITHOUT NAMED PARAMETERS:")
    print("  - Can only have one provider per type")
    print("  - No way to distinguish between different instances")
    print("  - Limited flexibility for complex applications")

    # With Named parameters - SOLUTION: Multiple instances of same type
    print("\n✅ WITH NAMED PARAMETERS:")
    print("  - Multiple providers of the same type")
    print("  - Clear distinction between instances")
    print("  - Better separation of concerns")
    print("  - More flexible architecture")

    print("\n📋 USE CASES:")
    print("  - Multiple database connections (primary/replica)")
    print("  - Different configuration sources (env/file/database)")
    print("  - Multiple service instances (user/admin)")
    print("  - Testing (mock/real implementations)")
    print("  - Multi-tenancy (different configs per tenant)")


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())

    # Demonstrate benefits
    asyncio.run(demonstrate_named_benefits())

    print("\n" + "=" * 60)
    print("NAMED PARAMETERS DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("Key benefits:")
    print("  ✅ Multiple providers of same type")
    print("  ✅ Clear instance identification")
    print("  ✅ Better architecture flexibility")
    print("  ✅ Improved separation of concerns")
