"""
Application orchestration for dependency injection framework.

This module provides the AppOrchestrator class that coordinates the high-level
workflow between different managers and handles application lifecycle orchestration.
"""

import asyncio
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


class AppOrchestrator:
    """Orchestrates the high-level workflow and coordination between DI managers."""

    def __init__(self, *components: Any) -> None:
        """Initialize the application orchestrator with components."""
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
            providers, values, {}, self._lifecycle, self._lifecycle_manager
        )
        self._validation_manager = ValidationManager(providers)
        self._invokable_executor = InvokableExecutor(
            self._builtin_service_manager, providers, values
        )

    def _request_shutdown(self) -> None:
        """Request shutdown of the application."""
        if not self._lifecycle_manager.is_started():
            # Schedule shutdown on the event loop
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
            # Get the current event loop
            loop = asyncio.get_running_loop()
            self._lifecycle_manager.set_loop(loop)

            # Set shutdown callback in built-in service manager
            self._builtin_service_manager.set_shutdown_callback(self._request_shutdown)

            # Start lifecycle hooks
            await self._lifecycle.start()

            # Execute all invokable functions using the executor
            await self._invokable_executor.execute_invokables(
                self._state_manager.get_invokables(), self.resolve
            )

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

        # Use error handler for graceful shutdown
        await self._error_handler.graceful_shutdown()

        # Mark state as stopped after shutdown completes
        self._state_manager.mark_stopped()

    async def run(self) -> None:
        """Run the application with proper orchestration and graceful shutdown."""
        await self.start()

        try:
            # Keep the app running until interrupted
            while self._state_manager.is_running():
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            print("\nReceived shutdown signal, cleaning up...")
        finally:
            await self.stop()

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
