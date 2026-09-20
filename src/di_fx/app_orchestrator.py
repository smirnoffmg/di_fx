"""
Application orchestration for dependency injection framework.

This module provides the AppOrchestrator class that coordinates the high-level
workflow between different managers and handles application lifecycle orchestration.
"""

import asyncio
import contextlib
import logging
import signal
from collections.abc import Iterator
from typing import Any

from .builtin_service_manager import BuiltinServiceManager
from .component_processor_manager import ComponentProcessorManager
from .dependency_resolver import DependencyResolver
from .error_handler import ErrorHandler
from .invokable_executor import InvokableExecutor
from .lifecycle import Lifecycle
from .lifecycle_manager import LifecycleManager
from .state_manager import StateManager
from .validation_manager import ValidationManager

logger = logging.getLogger(__name__)

#: Signals that mean "shut down" to a process supervisor.
_SHUTDOWN_SIGNALS = (signal.SIGINT, signal.SIGTERM)


class AppOrchestrator:
    """Orchestrates the high-level workflow and coordination between DI managers."""

    def __init__(self, *components: Any, validate: bool = True) -> None:
        """Initialize the application orchestrator with components."""
        self._validate_on_start = validate
        self._shutdown_requested = asyncio.Event()
        self._waiting_for_shutdown = False
        # Initialize managers
        self._component_processor_manager = ComponentProcessorManager()
        self._lifecycle = Lifecycle()
        self._lifecycle_manager = LifecycleManager()
        self._builtin_service_manager = BuiltinServiceManager()
        self._state_manager = StateManager()
        self._error_handler = ErrorHandler(self._lifecycle, self._lifecycle_manager)

        # Process components first
        for component in components:
            self._component_processor_manager.process_component(component)

        # Get processed components and set them in state manager
        providers = self._component_processor_manager.get_providers()
        values = self._component_processor_manager.get_values()
        invokables = self._component_processor_manager.get_invokables()
        self._state_manager.set_components(providers, values, invokables)

        # Initialize specialized managers
        self._resolver = DependencyResolver(
            providers,
            values,
            {},
            self._lifecycle,
            self._lifecycle_manager,
            self._builtin_service_manager,
        )
        self._validation_manager = ValidationManager(providers, values, invokables)
        self._invokable_executor = InvokableExecutor(
            self._builtin_service_manager, providers, values
        )

    def _request_shutdown(self) -> None:
        """Request shutdown of the application."""
        self._shutdown_requested.set()

        if self._waiting_for_shutdown:
            # run() is watching the event and will stop the application itself.
            return

        # Started through start() rather than run(), so nobody is waiting.
        if self._state_manager.is_running():
            loop = self._lifecycle_manager.get_loop()
            if loop and loop.is_running():
                loop.create_task(self.stop())

    async def resolve(self, type_: type[Any]) -> Any:
        """Resolve a dependency of the specified type."""
        return await self._resolver.resolve(type_)

    async def start(self) -> None:
        """Start the application lifecycle with proper orchestration."""
        if self._lifecycle_manager.is_started():
            return

        try:
            if self._validate_on_start:
                self.validate()

            # Get the current event loop
            loop = asyncio.get_running_loop()
            self._lifecycle_manager.set_loop(loop)

            # Set shutdown callback in built-in service manager
            self._builtin_service_manager.set_shutdown_callback(self._request_shutdown)

            # Initialization: running the invokables calls the constructors they
            # depend on, and those constructors are what append lifecycle hooks.
            # So this has to finish before the lifecycle is allowed to start.
            await self._invokable_executor.execute_invokables(
                self._state_manager.get_invokables(), self.resolve
            )

            # Execution: run the hooks collected during initialization.
            await self._lifecycle.start()

            # Mark lifecycle as started
            self._lifecycle_manager.start()
            self._state_manager.mark_running()

        except Exception as error:
            # Handle startup failure using error handler
            await self._error_handler.handle_startup_failure(error)
            raise

    async def stop(self) -> None:
        """Stop the application lifecycle and cleanup resources."""
        if not self._state_manager.is_running():
            return

        try:
            await self._error_handler.graceful_shutdown()
        finally:
            # The application is down either way; a failed hook must not leave the
            # state saying it is still running.
            self._state_manager.mark_stopped()

    async def run(self) -> None:
        """Run the application until it is asked to stop, then shut it down."""
        await self.start()

        self._waiting_for_shutdown = True
        try:
            with self._handle_shutdown_signals():
                await self._shutdown_requested.wait()
        finally:
            self._waiting_for_shutdown = False
            await self.stop()

    @contextlib.contextmanager
    def _handle_shutdown_signals(self) -> Iterator[None]:
        """Turn SIGINT and SIGTERM into a shutdown request for the duration of run().

        add_signal_handler is unavailable on some platforms (Windows); there the
        signal keeps its default behaviour and KeyboardInterrupt still works.
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

    def create_task(self, coro: Any) -> asyncio.Task[Any]:
        """Create and track an asyncio task."""
        return self._lifecycle_manager.create_task(coro)

    def validate(self) -> None:
        """Validate the dependency graph before starting the application."""
        self._validation_manager.validate()
        self._state_manager.mark_initialized()

    def get_providers(self) -> dict[type[Any], Any]:
        """Get the processed providers."""
        return self._state_manager.get_providers()

    def get_values(self) -> dict[type[Any], Any]:
        """Get the processed values."""
        return self._state_manager.get_values()

    def get_invokables(self) -> list[Any]:
        """Get the processed invokables."""
        return self._state_manager.get_invokables()

    def has_provider(self, type_: type[Any]) -> bool:
        """Check if a provider exists for a type."""
        return self._state_manager.has_provider(type_)

    def has_value(self, type_: type[Any]) -> bool:
        """Check if a value exists for a type."""
        return self._state_manager.has_value(type_)

    def is_running(self) -> bool:
        """Check if the application is currently running."""
        return self._state_manager.is_running()

    def is_initialized(self) -> bool:
        """Check if the application has been initialized."""
        return self._state_manager.is_initialized()

    def get_component_counts(self) -> dict[str, int]:
        """Get counts of different component types."""
        return self._state_manager.get_component_counts()

    def get_state_summary(self) -> dict[str, Any]:
        """Get a comprehensive summary of the application state."""
        return self._state_manager.get_state_summary()

    def get_error_handler(self) -> ErrorHandler:
        """Get the error handler for external error handling needs."""
        return self._error_handler
