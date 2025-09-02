"""
Lifecycle management for dependency injection framework.

This module provides classes for managing application startup and
shutdown hooks.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Hook:
    """A lifecycle hook that runs during application startup or shutdown."""

    on_start: Callable[[], Awaitable[None]] | None = None
    on_stop: Callable[[], Awaitable[None]] | None = None
    timeout: float = 30.0
    name: str | None = None

    def __post_init__(self) -> None:
        if self.name is None:
            if self.on_start:
                self.name = f"{self.on_start.__name__}_hook"
            elif self.on_stop:
                self.name = f"{self.on_stop.__name__}_hook"
            else:
                self.name = "unnamed_hook"


class Lifecycle:
    """Manages application lifecycle hooks."""

    def __init__(self) -> None:
        self._hooks: list[Hook] = []
        self._started = False
        self._stopped = False

    def append(self, hook: Hook) -> None:
        """Add a lifecycle hook."""
        if self._started:
            raise RuntimeError("Cannot add hooks after lifecycle has started")
        self._hooks.append(hook)

    async def start(self) -> None:
        """Execute all startup hooks."""
        if self._started:
            return

        self._started = True
        for hook in self._hooks:
            if hook.on_start:
                await hook.on_start()

    async def stop(self) -> None:
        """Execute all shutdown hooks in reverse order."""
        if self._stopped:
            return

        self._stopped = True
        for hook in reversed(self._hooks):
            if hook.on_stop:
                await hook.on_stop()

    def __len__(self) -> int:
        return len(self._hooks)

    def __iter__(self) -> Any:
        return iter(self._hooks)
