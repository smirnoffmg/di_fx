"""Checking the graph before anything runs.

Shows: validate() as a pre-flight check, and what the error looks like when a
dependency is missing.
"""

import asyncio
from typing import Annotated

from di_fx import App, Component, Invoke, Provide, ValidationError

# Use Annotated types to create distinct types for dependency injection
DatabaseType = Annotated[str, "database"]
SchedulerType = Annotated[str, "scheduler"]
ConfigType = Annotated[dict, "config"]


def create_database_config() -> ConfigType:
    """Create database configuration."""
    return {"url": "postgresql://localhost/mydb", "pool_size": 10}


def create_database(config: ConfigType) -> DatabaseType:
    """Create database connection."""
    print(f"Connecting to database: {config['url']}")
    return "Database"


def create_scheduler() -> SchedulerType:
    """Create HTTP scheduler."""
    print("Creating HTTP scheduler")
    return "Scheduler"


def schedule_jobs(scheduler: SchedulerType) -> str:
    """Setup HTTP jobs."""
    print(f"Scheduling jobs for {scheduler}")
    return "Jobs scheduled"


def seed_database(database: DatabaseType) -> str:
    """Seed database with initial data."""
    print(f"Seeding {database} with initial data")
    return "Database seeded"


def print_startup_info(database: DatabaseType, scheduler: SchedulerType) -> str:
    """Print startup information."""
    print(f"Application started with {database} and {scheduler}")
    return "Startup info printed"


# Create modules for different concerns
DatabaseModule = Component(
    "database",
    Provide(create_database_config, create_database),
    Invoke(seed_database),
)

SchedulerModule = Component(
    "scheduler",
    Provide(create_scheduler),
    Invoke(schedule_jobs),
)


# Group all modules together
def create_app() -> Component:
    """Create application options."""
    return Component(
        DatabaseModule,
        SchedulerModule,
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
    async with app:
        print("Application is running...")

        # Resolve dependencies to verify they work
        database = await app.resolve(DatabaseType)
        scheduler = await app.resolve(SchedulerType)
        config = await app.resolve(ConfigType)

        print(f"Resolved: {database}, {scheduler}, {config}")

        # Simulate some work
        await asyncio.sleep(0.1)

    print("Application stopped!")


async def demonstrate_validation_failure() -> None:
    """Demonstrate what happens when validation fails."""
    print("\n" + "=" * 50)
    print("DEMONSTRATING VALIDATION FAILURE")
    print("=" * 50)

    # Create an app with a missing dependency. Each provider needs a return type
    # of its own: providers are keyed by return type, so two functions returning
    # str would be two providers competing for the same key.
    ServiceA = Annotated[str, "service_a"]
    ServiceB = Annotated[str, "service_b"]

    def create_service_a(service_b: ServiceB) -> ServiceA:
        return f"ServiceA with {service_b}"

    def create_service_b(missing: int) -> ServiceB:
        return f"ServiceB with {missing}"

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
