"""
Lifecycle management for dependency injection framework.

This module provides classes for managing application startup and
shutdown hooks.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class HookTimeoutError(RuntimeError):
    """Raised when a lifecycle hook exceeds its timeout."""


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


@dataclass
class _Entry:
    """One shutdownable thing, in the order it joined the lifecycle."""

    name: str
    timeout: float
    on_start: Callable[[], Awaitable[None]] | None = None
    on_stop: Callable[[], Awaitable[None]] | None = None
    hook: Hook | None = None
    started: bool = False


def _closer(generator: Any, name: str) -> Callable[[], Awaitable[None]]:
    """Resume a provider generator past its yield so its cleanup code runs.

    aclose() alone throws GeneratorExit at the suspension point, which skips any
    plain statements after the yield and only honours try/finally. Advancing the
    generator instead runs both forms, the way @asynccontextmanager does.
    """

    async def close() -> None:
        try:
            await anext(generator)
        except StopAsyncIteration:
            return
        await generator.aclose()
        raise RuntimeError(f"Provider {name} yielded more than once")

    return close


class Lifecycle:
    """Manages application lifecycle hooks."""

    def __init__(self) -> None:
        self._entries: list[_Entry] = []
        self._started = False
        self._stopped = False

    def append(self, hook: Hook) -> None:
        """Add a lifecycle hook."""
        if self._started:
            raise RuntimeError("Cannot add hooks after lifecycle has started")
        self._entries.append(
            _Entry(
                name=hook.name or "unnamed_hook",
                timeout=hook.timeout,
                on_start=hook.on_start,
                on_stop=hook.on_stop,
                hook=hook,
            )
        )

    def add_resource(self, generator: Any, name: str, timeout: float = 30.0) -> None:
        """Register an async generator provider for shutdown.

        The generator has already run up to its yield by the time it gets here, so
        it joins the same ordered list as the hooks and is marked started at once:
        it holds a live resource whether or not the lifecycle ever starts.
        """
        self._entries.append(
            _Entry(
                name=name,
                timeout=timeout,
                on_stop=_closer(generator, name),
                started=True,
            )
        )

    async def start(self) -> None:
        """Execute all startup hooks."""
        if self._started:
            return

        self._started = True
        for entry in self._entries:
            if entry.on_start is not None:
                try:
                    await asyncio.wait_for(entry.on_start(), entry.timeout)
                except TimeoutError as error:
                    await self._rollback()
                    raise HookTimeoutError(
                        f"Hook {entry.name} did not start within {entry.timeout}s"
                    ) from error
                except Exception:
                    await self._rollback()
                    raise
            entry.started = True

    async def stop(self) -> None:
        """Execute shutdown hooks in reverse order.

        Only what actually started is stopped. Every remaining hook runs even if an
        earlier one fails, and the failures are raised together rather than dropped.
        """
        if self._stopped:
            return

        self._stopped = True
        errors = await self._shutdown()
        if errors:
            raise ExceptionGroup("errors during shutdown", errors)

    async def _rollback(self) -> None:
        """Undo a partial startup without masking the error that caused it."""
        self._stopped = True
        for error in await self._shutdown():
            logger.error("Error while rolling back a failed startup: %s", error)

    async def _shutdown(self) -> list[Exception]:
        errors: list[Exception] = []
        for entry in reversed(self._entries):
            if not entry.started or entry.on_stop is None:
                continue
            try:
                await asyncio.wait_for(entry.on_stop(), entry.timeout)
            except TimeoutError as error:
                errors.append(
                    HookTimeoutError(
                        f"Hook {entry.name} did not stop within {entry.timeout}s"
                    ).with_traceback(error.__traceback__)
                )
            except Exception as error:
                errors.append(error)
            entry.started = False
        return errors

    def __len__(self) -> int:
        return len(self._hooks())

    def __iter__(self) -> Iterator[Hook]:
        return iter(self._hooks())

    def _hooks(self) -> list[Hook]:
        return [entry.hook for entry in self._entries if entry.hook is not None]
