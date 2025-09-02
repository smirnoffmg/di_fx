"""
Invokable execution for dependency injection framework.

This module provides an InvokableExecutor class that handles all
invokable execution logic, separating concerns from the main App class.
"""

from collections.abc import Callable
from typing import Any

from .builtin_service_manager import BuiltinServiceManager
from .invoke import Invokable


class InvokableExecutor:
    """Handles execution of invokable functions during application startup."""

    def __init__(
        self,
        builtin_service_manager: BuiltinServiceManager,
        providers: dict[type[Any], Any],
        values: dict[type[Any], Any],
    ) -> None:
        """Initialize the invokable executor.

        Args:
            builtin_service_manager: Manager for built-in services like DotGraph and Shutdowner
            providers: Dictionary of type -> provider mappings
            values: Dictionary of type -> value mappings
        """
        self._builtin_service_manager = builtin_service_manager
        self._providers = providers
        self._values = values

    async def execute_invokables(
        self,
        invokables: list[Invokable],
        resolve_dependency: Callable[[type[Any]], Any],
    ) -> None:
        """Execute all invokable functions with proper dependency resolution.

        Args:
            invokables: List of invokable functions to execute
            resolve_dependency: Function to resolve dependencies (typically App.resolve)
        """
        for invokable in invokables:
            try:
                await self._execute_single_invokable(invokable, resolve_dependency)
            except Exception as e:
                # Log error but continue with other invokables
                print(f"Error executing {invokable.name}: {e}")
                raise

    async def _execute_single_invokable(
        self, invokable: Invokable, resolve_dependency: Callable[[type[Any]], Any]
    ) -> None:
        """Execute a single invokable function.

        Args:
            invokable: The invokable function to execute
            resolve_dependency: Function to resolve dependencies
        """
        # Resolve dependencies for the invokable function
        dependencies: list[Any] = []
        if invokable.dependencies:
            dependencies = await self._resolve_invokable_dependencies(
                invokable.dependencies, resolve_dependency
            )

        # Execute the function
        result = invokable.func(*dependencies)

        # Handle async functions
        if hasattr(result, "__await__"):
            await result

    async def _resolve_invokable_dependencies(
        self, dep_types: list[type[Any]], resolve_dependency: Callable[[type[Any]], Any]
    ) -> list[Any]:
        """Resolve dependencies for an invokable function.

        Args:
            dep_types: List of dependency types to resolve
            resolve_dependency: Function to resolve dependencies

        Returns:
            List of resolved dependency instances
        """
        dependencies: list[Any] = []

        for dep_type in dep_types:
            # Handle built-in services specially
            from .dotgraph import DotGraph as DotGraphClass
            from .shutdowner import Shutdowner as ShutdownClass

            if dep_type == DotGraphClass:
                dependencies.append(
                    self._builtin_service_manager.get_dotgraph(
                        self._providers, self._values
                    )
                )
            elif dep_type == ShutdownClass:
                dependencies.append(self._builtin_service_manager.get_shutdowner())
            else:
                dependencies.append(await resolve_dependency(dep_type))

        return dependencies

    def get_invokable_count(self, invokables: list[Invokable]) -> int:
        """Get the number of invokables to execute."""
        return len(invokables)

    def has_invokables(self, invokables: list[Invokable]) -> bool:
        """Check if there are any invokables to execute."""
        return bool(invokables)
