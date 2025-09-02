"""Pytest configuration and fixtures for di_fx tests."""

import asyncio
from collections.abc import AsyncGenerator

import pytest

from di_fx import App, Hook, Provide, Supply


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def basic_app() -> AsyncGenerator[App, None]:
    """Create a basic DI app for testing."""

    # Simple test services
    def create_config() -> dict:
        return {"debug": True, "port": 8000}

    def create_service(config: dict) -> str:
        return f"Service with config: {config}"

    app = App(Provide(create_config, create_service), Supply("test_value"))

    async with app.lifecycle():
        yield app


@pytest.fixture
async def lifecycle_app() -> AsyncGenerator[App, None]:
    """Create a DI app with lifecycle hooks for testing."""

    async def start_hook():
        pass

    async def stop_hook():
        pass

    def create_lifecycle_service(lifecycle) -> str:
        lifecycle.append(Hook(on_start=start_hook, on_stop=stop_hook))
        return "LifecycleService"

    app = App(Provide(create_lifecycle_service))

    async with app.lifecycle():
        yield app
