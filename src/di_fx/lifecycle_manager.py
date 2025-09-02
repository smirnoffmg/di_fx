"""
Lifecycle management for dependency injection framework.

This module provides a LifecycleManager class that handles all
lifecycle-related concerns, separating them from the main App class.
"""

import asyncio
from typing import Any


class LifecycleManager:
    """Manages application lifecycle including tasks, async generators, and start/stop operations."""

    def __init__(self) -> None:
        """Initialize the lifecycle manager."""
        self._started = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tasks: set[asyncio.Task[Any]] = set()
        self._async_generators: dict[type[Any], Any] = {}

    def is_started(self) -> bool:
        """Check if the lifecycle has been started."""
        return self._started

    def get_loop(self) -> asyncio.AbstractEventLoop | None:
        """Get the current event loop."""
        return self._loop

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the current event loop."""
        self._loop = loop

    def create_task(self, coro: Any) -> asyncio.Task[Any]:
        """Create and track an asyncio task."""
        if not self._started:
            raise RuntimeError("Cannot create tasks before lifecycle is started")

        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        task = self._loop.create_task(coro)
        self._tasks.add(task)

        # Remove task from tracking when it's done
        task.add_done_callback(self._tasks.discard)

        return task

    def add_async_generator(self, type_: type[Any], generator: Any) -> None:
        """Add an async generator for lifecycle management."""
        self._async_generators[type_] = generator

    def start(self) -> None:
        """Mark the lifecycle as started."""
        self._started = True

    async def stop(self) -> None:
        """Stop the lifecycle and cleanup resources."""
        if not self._started:
            return

        # Cancel all running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Stop async generators (close resources)
        for generator in self._async_generators.values():
            if hasattr(generator, "aclose"):
                await generator.aclose()
            elif hasattr(generator, "close"):
                generator.close()

        # Reset state
        self._started = False
        self._loop = None
        self._tasks.clear()
        self._async_generators.clear()

    def get_task_count(self) -> int:
        """Get the number of active tasks."""
        return len(self._tasks)

    def get_generator_count(self) -> int:
        """Get the number of async generators."""
        return len(self._async_generators)
