#!/usr/bin/env python3
"""
Basic usage example for di_fx dependency injection framework.

This example demonstrates the core functionality:
- Service providers
- Configuration values
- Lifecycle hooks
- Async integration
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from di_fx import Component, Hook, Lifecycle, Provide, Supply


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str
    pool_size: int = 10


class Database:
    """Simple database mock."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connected = False

    async def connect(self) -> None:
        """Connect to database."""
        print(f"Connecting to {self.config.url} with pool size {self.config.pool_size}")
        self.connected = True

    async def close(self) -> None:
        """Close database connection."""
        print("Closing database connection")
        self.connected = False

    async def query(self, sql: str) -> dict:
        """Execute a query."""
        if not self.connected:
            raise RuntimeError("Database not connected")
        return {"result": f"Query: {sql}", "rows": 1}


class UserService:
    """User service that depends on database."""

    def __init__(self, db: Database):
        self.db = db

    async def get_user(self, user_id: str) -> dict:
        """Get a user by ID."""
        result = await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return {"id": user_id, "name": "John Doe", "db_result": result}


async def new_database(config: DatabaseConfig) -> AsyncIterator[Database]:
    """Create and manage database connection."""
    db = Database(config)
    await db.connect()
    try:
        yield db
    finally:
        await db.close()


def new_user_service(db: Database) -> UserService:
    """Create user service."""
    return UserService(db)


def new_background_worker(lifecycle: Lifecycle, user_service: UserService) -> str:
    """Create background worker with lifecycle hooks."""
    worker_name = "UserDataProcessor"

    async def start_worker() -> None:
        print(f"Starting {worker_name}")

    async def stop_worker() -> None:
        print(f"Stopping {worker_name}")

    lifecycle.append(Hook(on_start=start_worker, on_stop=stop_worker, name=worker_name))

    return worker_name


async def main() -> None:
    """Main application function."""
    # Create the application
    app = Component(
        Provide(
            new_database,
            new_user_service,
            new_background_worker,
        ),
        Supply(
            DatabaseConfig(url="postgresql://localhost/mydb", pool_size=5),
        ),
    )

    # Use the application
    async with app.lifecycle():
        print("Application started!")

        # Resolve dependencies
        user_service = await app.resolve(UserService)
        _ = await app.resolve(str)  # Background worker

        # Use the service
        user = await user_service.get_user("123")
        print(f"User: {user}")

        print("Application running...")
        await asyncio.sleep(1)  # Simulate work

    print("Application stopped!")


if __name__ == "__main__":
    asyncio.run(main())
