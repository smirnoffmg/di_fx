"""The application: initialization, then execution."""

import asyncio
import contextlib
import logging
import signal
from collections.abc import AsyncIterator, Iterator
from typing import Any, TypeVar

from .dotgraph import DotGraph
from .graph import Graph, flatten, validate
from .lifecycle import Lifecycle
from .resolver import Resolver
from .shutdowner import Shutdowner

T = TypeVar("T", bound=Any)

logger = logging.getLogger(__name__)

#: Signals that mean "shut down" to a process supervisor.
_SHUTDOWN_SIGNALS = (signal.SIGINT, signal.SIGTERM)


class App:
    """A runnable application built from registrations.

    Its life has two phases, as in Uber-Fx. During *initialization* the invokables
    run, calling the constructors they need in dependency order; those constructors
    are what append lifecycle hooks. During *execution* the hooks run, the
    application waits, and then everything unwinds in reverse.
    """

    def __init__(self, *registrations: Any, validate: bool = True) -> None:
        self._graph: Graph = flatten(*registrations)
        self._validate_on_start = validate

        self._lifecycle = Lifecycle()
        self._shutdowner = Shutdowner(self._request_shutdown)
        self._resolver = Resolver(
            self._graph,
            self._lifecycle,
            {
                Lifecycle: lambda: self._lifecycle,
                Shutdowner: lambda: self._shutdowner,
                DotGraph: lambda: DotGraph(self._graph.providers, self._graph.values),
            },
        )

        self._started = False
        self._stopped = False
        self._tasks: set[asyncio.Task[Any]] = set()
        self._shutdown_requested = asyncio.Event()
        self._waiting_for_shutdown = False

    @property
    def graph(self) -> Graph:
        return self._graph

    def validate(self) -> None:
        """Check the dependency graph without building anything."""
        validate(self._graph)

    async def resolve(self, type_: type[T]) -> T:
        """Build an instance of a type, along with whatever it needs."""
        return await self._resolver.resolve(type_)

    async def start(self) -> None:
        """Run the invokables, then the startup hooks."""
        if self._started:
            return

        if self._validate_on_start:
            self.validate()

        try:
            for invokable in self._graph.invokables:
                await self._invoke(invokable)
            await self._lifecycle.start()
        except BaseException:
            await self._cleanup_after_failed_start()
            raise

        self._started = True

    async def stop(self) -> None:
        """Cancel tracked tasks, then unwind the lifecycle."""
        if self._stopped or not self._started:
            return

        self._stopped = True
        self._started = False
        await self._cancel_tasks()
        await self._lifecycle.stop()

    async def run(self) -> None:
        """Start, wait for a shutdown request, then stop."""
        await self.start()

        self._waiting_for_shutdown = True
        try:
            with self._handle_shutdown_signals():
                await self._shutdown_requested.wait()
        finally:
            self._waiting_for_shutdown = False
            await self.stop()

    async def __aenter__(self) -> "App":
        await self.start()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.stop()

    def create_task(self, coro: Any) -> asyncio.Task[Any]:
        """Create a task the application will cancel when it stops."""
        if not self._started:
            raise RuntimeError("Cannot create tasks before the application is started")
        task = asyncio.get_running_loop().create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def is_running(self) -> bool:
        return self._started

    async def _invoke(self, invokable: Any) -> None:
        dependencies = [await self.resolve(dep) for dep in invokable.dependencies]
        try:
            result = invokable.func(*dependencies)
        except Exception as error:
            logger.error("Error executing %s: %s", invokable.name, error)
            raise
        if hasattr(result, "__await__"):
            await result

    async def _cleanup_after_failed_start(self) -> None:
        """Release whatever the failed start had already built."""
        try:
            await self._cancel_tasks()
            await self._lifecycle.stop()
        except Exception as error:
            # The error that failed the start is the one worth raising.
            logger.error("Cleanup after a failed start also failed: %s", error)

    async def _cancel_tasks(self) -> None:
        # Iterate a copy: awaiting a cancelled task lets its done callback discard
        # it from self._tasks while we are still walking it.
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._tasks.clear()

    def _request_shutdown(self) -> None:
        self._shutdown_requested.set()

        if self._waiting_for_shutdown:
            # run() is watching the event and will stop the application itself.
            return

        if self._started:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.stop())

    @contextlib.contextmanager
    def _handle_shutdown_signals(self) -> Iterator[None]:
        """Turn SIGINT and SIGTERM into a shutdown request, for this run only.

        add_signal_handler is unavailable on some platforms (Windows); there the
        signals keep their default behaviour and KeyboardInterrupt still works.
        """
        loop = asyncio.get_running_loop()
        installed = []
        for sig in _SHUTDOWN_SIGNALS:
            try:
                loop.add_signal_handler(sig, self._request_shutdown)
            except (NotImplementedError, RuntimeError, ValueError):
                logger.debug("No signal handler installed for %s", sig)
            else:
                installed.append(sig)
        try:
            yield
        finally:
            for sig in installed:
                loop.remove_signal_handler(sig)

    @contextlib.asynccontextmanager
    async def lifecycle(self) -> AsyncIterator["App"]:
        """Deprecated alias for using the application as a context manager."""
        async with self as app:
            yield app
