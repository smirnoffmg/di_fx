"""
Lifecycle management for dependency injection framework.

This module provides a LifecycleManager class that handles all
lifecycle-related concerns, separating them from the main App class.
"""

import asyncio
from typing import Any


class LifecycleManager:
    """Manages the event loop and the tasks created through the application."""

    def __init__(self) -> None:
        """Initialize the lifecycle manager."""
        self._started = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tasks: set[asyncio.Task[Any]] = set()

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

    def start(self) -> None:
        """Mark the lifecycle as started."""
        self._started = True

    async def stop(self) -> None:
        """Cancel every tracked task and reset the loop state."""
        if not self._started:
            return

        # Iterate a copy: awaiting a cancelled task lets its done callback
        # discard it from self._tasks while we are still walking it.
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Reset state
        self._started = False
        self._loop = None
        self._tasks.clear()

    def get_task_count(self) -> int:
        """Get the number of active tasks."""
        return len(self._tasks)
