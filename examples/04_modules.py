"""Composing an application out of named modules.

Shows: Component as a named group of registrations, nesting, and Annotated aliases
to keep two providers that both return str from colliding.
"""

import asyncio
from typing import Annotated

from di_fx import App, Component, Invoke, Provide

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


def report(
    database: DatabaseType, scheduler: SchedulerType, config: ConfigType
) -> None:
    """Asking for the three types here is what causes them to be built.

    It happens during initialization, which is the only phase where a constructor
    may still append a lifecycle hook. Resolving from inside the `async with`
    block below would be too late for that.
    """
    print(f"Resolved: {database}, {scheduler}, {config}")


async def main() -> None:
    """Main application function."""
    print("Starting di_fx application built from modules...")

    app = App(create_app(), Invoke(report))

    async with app:
        print("Application is running...")
        await asyncio.sleep(0.1)

    print("Application stopped!")


if __name__ == "__main__":
    asyncio.run(main())
