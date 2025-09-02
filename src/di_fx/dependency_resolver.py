"""
Dependency resolution for dependency injection framework.

This module provides a DependencyResolver class that handles all
dependency resolution logic, separating concerns from the main App class.
"""

from typing import Any, TypeVar

from .lifecycle import Lifecycle
from .lifecycle_manager import LifecycleManager
from .named import get_named_type_info, is_named_type

T = TypeVar("T", bound=Any)


class DependencyResolver:
    """Handles dependency resolution for the DI framework."""

    def __init__(
        self,
        providers: dict[type[Any], Any],
        values: dict[type[Any], Any],
        instances: dict[type[Any], Any],
        lifecycle: Lifecycle,
        lifecycle_manager: LifecycleManager,
    ) -> None:
        """Initialize the dependency resolver.

        Args:
            providers: Dictionary of type -> provider mappings
            values: Dictionary of type -> value mappings
            instances: Dictionary of cached instances
            lifecycle: Lifecycle instance for built-in services
            lifecycle_manager: LifecycleManager for managing async generators
        """
        self._providers = providers
        self._values = values
        self._instances = instances
        self._lifecycle = lifecycle
        self._lifecycle_manager = lifecycle_manager
        self._builtin_dotgraph: Any = None
        self._builtin_shutdowner: Any = None

    async def resolve(self, type_: type[T]) -> T:
        """Resolve a dependency of the specified type."""
        if type_ in self._instances:
            return self._instances[type_]  # type: ignore

        if type_ in self._values:
            return self._values[type_].value  # type: ignore

        # Handle built-in services
        instance = await self._resolve_builtin_service(type_)
        if instance is not None:
            return instance  # type: ignore

        # Handle Named types
        if is_named_type(type_):
            return await self._resolve_named_type(type_)  # type: ignore

        # Handle regular providers
        if type_ not in self._providers:
            raise KeyError(f"No provider registered for type {type_.__name__}")

        provider = self._providers[type_]
        return await self._create_instance(provider)  # type: ignore

    async def _resolve_builtin_service(self, type_: type[Any]) -> Any | None:
        """Resolve built-in services like Lifecycle, DotGraph, and Shutdowner."""
        # Special case: provide Lifecycle instance
        if type_ == Lifecycle:
            return self._lifecycle

        # Special case: provide DotGraph instance
        from .dotgraph import DotGraph as DotGraphClass

        if type_ == DotGraphClass:
            if self._builtin_dotgraph is None:
                from .dotgraph import DotGraph

                self._builtin_dotgraph = DotGraph(self._providers, self._values)
            return self._builtin_dotgraph

        # Special case: provide Shutdowner instance
        from .shutdowner import Shutdowner as ShutdownerClass

        if type_ == ShutdownerClass:
            if self._builtin_shutdowner is None:
                from .shutdowner import Shutdowner

                # We need a callback function - this will be set by the App
                self._builtin_shutdowner = Shutdowner(lambda: None)
            return self._builtin_shutdowner

        return None

    async def _resolve_named_type(self, type_: type[Any]) -> Any:
        """Resolve a Named type dependency."""
        named_info = get_named_type_info(type_)
        if named_info is None:
            raise KeyError(f"Invalid named type: {type_.__name__}")

        name, base_type = named_info

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

        return await self._create_instance(provider)

    async def _create_instance(self, provider: Any) -> Any:
        """Create an instance from a provider."""
        # Resolve dependencies
        dependencies: list[Any] = []
        if provider.dependencies:
            for dep_type in provider.dependencies:
                if dep_type in self._instances:
                    dependencies.append(self._instances[dep_type])
                elif dep_type in self._values:
                    dependencies.append(self._values[dep_type].value)
                elif dep_type == Lifecycle:
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
            self._lifecycle_manager.add_async_generator(type(instance), generator)

        # Store instance if singleton
        if provider.singleton:
            self._instances[provider.return_type] = instance

        return instance

    def set_shutdown_callback(self, callback: Any) -> None:
        """Set the shutdown callback for the built-in Shutdowner service."""
        if self._builtin_shutdowner is not None:
            self._builtin_shutdowner._shutdown_callback = callback
