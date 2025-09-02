"""
Main application container for dependency injection framework.

This module provides the App class that orchestrates dependency injection
with proper asyncio event loop integration.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from .dotgraph import DotGraph
from .invoke import Invokable, Invoke
from .lifecycle import Lifecycle
from .module import Module
from .options import Options
from .provide import Provide, Provider
from .shutdowner import Shutdowner
from .supply import Supply, Value
from .validation import validate_dependency_graph

T = TypeVar("T", bound=Any)


class App:
    """Main dependency injection application container with asyncio integration."""

    def __init__(self, *components: Any) -> None:
        self._providers: dict[type[Any], Provider] = {}
        self._values: dict[type[Any], Value] = {}
        self._invokables: list[Invokable] = []
        self._lifecycle = Lifecycle()

        # Auto-provide built-in services (like Uber-Fx)
        self._auto_provide_builtin_services()
        self._instances: dict[type[Any], Any] = {}
        self._async_generators: dict[type[Any], Any] = {}
        self._started = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tasks: set[asyncio.Task[Any]] = set()

        # Process components
        for component in components:
            self._process_component(component)

    def _auto_provide_builtin_services(self) -> None:
        """Auto-provide built-in services like Uber-Fx does."""
        # Initialize built-in services
        # Note: These will be updated with final state when needed
        self._builtin_dotgraph = None
        self._builtin_shutdowner = None

    def _request_shutdown(self) -> None:
        """Request shutdown of the application."""
        if not self._stopped:
            # Schedule shutdown on the event loop
            if self._loop and self._loop.is_running():
                self._loop.create_task(self._stop())

    def _process_component(self, component: Any) -> None:
        """Process a single component and extract its providers, values, and invokables."""
        if isinstance(component, Provide):
            self._providers.update(
                {provider.return_type: provider for provider in component}
            )
        elif isinstance(component, Supply):
            self._values.update({value.type_: value for value in component})
        elif isinstance(component, Invoke):
            self._invokables.extend(component.get_invokables())
        elif isinstance(component, Module):
            # Extract components from module
            for provider in component.get_providers():
                self._providers.update({p.return_type: p for p in provider})
            for supply in component.get_supplies():
                self._values.update({v.type_: v for v in supply})
            self._invokables.extend(component.get_invokables())
        elif isinstance(component, Options):
            # Extract components from options
            for provider in component.get_providers():
                self._providers.update({p.return_type: p for p in provider})
            for supply in component.get_supplies():
                self._values.update({v.type_: v for v in supply})
            self._invokables.extend(component.get_invokables())
        else:
            raise ValueError(f"Unknown component type: {type(component)}")

    async def resolve(self, type_: type[T]) -> T:
        """Resolve a dependency of the specified type."""
        if type_ in self._instances:
            return self._instances[type_]  # type: ignore

        if type_ in self._values:
            return self._values[type_].value  # type: ignore

        # Special case: provide Lifecycle instance
        from .lifecycle import Lifecycle as LifecycleClass

        if type_ == LifecycleClass:
            return self._lifecycle  # type: ignore

        # Special case: provide DotGraph instance
        from .dotgraph import DotGraph as DotGraphClass

        if type_ == DotGraphClass:
            return DotGraph(self._providers, self._values)  # type: ignore

        # Special case: provide Shutdowner instance
        from .shutdowner import Shutdowner as ShutdownerClass

        if type_ == ShutdownerClass:
            return Shutdowner(self._request_shutdown)  # type: ignore

        # Check if this is a Named type
        from .named import get_named_type_info, is_named_type

        if is_named_type(type_):
            # For Named types, we need to find a provider that matches the name
            name, base_type = get_named_type_info(type_)

            # Look for a provider that returns this Named type
            if type_ in self._providers:
                provider = self._providers[type_]
            else:
                # Fallback: look for base type provider
                if base_type in self._providers:
                    provider = self._providers[base_type]
                else:
                    raise KeyError(
                        f"No provider registered for named type {name}:{base_type.__name__}"
                    )
        elif type_ not in self._providers:
            raise KeyError(f"No provider registered for type {type_.__name__}")
        else:
            provider = self._providers[type_]

        # Resolve dependencies
        dependencies = []
        for dep_type in provider.dependencies:
            if dep_type in self._instances:
                dependencies.append(self._instances[dep_type])
            elif dep_type in self._values:
                dependencies.append(self._values[dep_type].value)
            elif dep_type == LifecycleClass:
                dependencies.append(self._lifecycle)
            else:
                # Recursively resolve dependency
                dependencies.append(await self.resolve(dep_type))

        # Create instance
        instance = provider.constructor(*dependencies)

        # Handle async constructors
        if hasattr(instance, "__await__"):
            instance = await instance

        # Handle async generators (for lifecycle management)
        if hasattr(instance, "__aiter__"):
            # Store the original generator for lifecycle management
            generator = instance
            # Get the first yielded value
            async for value in generator:
                instance = value
                break
            # Store the generator to manage its lifecycle
            self._async_generators[type_] = generator

        # Store instance if singleton
        if provider.singleton:
            self._instances[type_] = instance

        return instance  # type: ignore

    async def start(self) -> None:
        """Start the application lifecycle with asyncio integration."""
        if self._started:
            return

        # Get the current event loop
        self._loop = asyncio.get_running_loop()

        # Start lifecycle hooks
        await self._lifecycle.start()

        # Initialize built-in services with current state
        if self._builtin_dotgraph is None:
            from .dotgraph import DotGraph

            self._builtin_dotgraph = DotGraph(self._providers, self._values)

        if self._builtin_shutdowner is None:
            from .shutdowner import Shutdowner

            self._builtin_shutdowner = Shutdowner(self._request_shutdown)

        # Execute all invokable functions
        for invokable in self._invokables:
            try:
                # Resolve dependencies for the invokable function
                dependencies = []
                if invokable.dependencies:
                    for dep_type in invokable.dependencies:
                        # Handle built-in services specially
                        from .dotgraph import DotGraph as DotGraphClass
                        from .shutdowner import Shutdowner as ShutdownerClass

                        if dep_type == DotGraphClass:
                            dependencies.append(self._builtin_dotgraph)
                        elif dep_type == ShutdownerClass:
                            dependencies.append(self._builtin_shutdowner)
                        else:
                            dependencies.append(await self.resolve(dep_type))

                # Execute the function
                result = invokable.func(*dependencies)

                # Handle async functions
                if hasattr(result, "__await__"):
                    await result

            except Exception as e:
                # Log error but continue with other invokables
                print(f"Error executing {invokable.name}: {e}")
                raise

        self._started = True

    async def stop(self) -> None:
        """Stop the application lifecycle and cleanup asyncio resources."""
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

        # Stop lifecycle hooks
        await self._lifecycle.stop()
        self._started = False
        self._loop = None

    def create_task(self, coro: Any) -> asyncio.Task[Any]:
        """Create and track an asyncio task."""
        if not self._started:
            raise RuntimeError("Cannot create tasks before app is started")

        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        task = self._loop.create_task(coro)
        self._tasks.add(task)

        # Remove task from tracking when it's done
        task.add_done_callback(self._tasks.discard)

        return task

    @asynccontextmanager
    async def lifecycle(self) -> Any:
        """Context manager for application lifecycle."""
        try:
            # Don't start lifecycle yet - let dependencies resolve first
            yield self
            # Start the application after dependencies are resolved
            await self.start()
        finally:
            if self._started:
                await self.stop()

    async def run(self) -> None:
        """Run the application with proper asyncio event loop integration."""
        await self.start()

        # TODO: Implement signal handling for graceful shutdown
        # For now, this is a placeholder that keeps the app running

        try:
            # Keep the app running until interrupted
            while self._started:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            await self.stop()

    def __len__(self) -> int:
        return len(self._providers) + len(self._values)

    def has_provider(self, type_: type[T]) -> bool:
        """Check if a provider exists for a type."""
        return type_ in self._providers

    def has_value(self, type_: type[T]) -> bool:
        """Check if a value exists for a type."""
        return type_ in self._values

    def validate(self) -> None:
        """Validate the dependency graph before starting the application.

        This checks for:
        - Missing dependencies
        - Circular dependencies

        Raises:
            ValidationError: If validation fails
        """
        validate_dependency_graph(self._providers)
