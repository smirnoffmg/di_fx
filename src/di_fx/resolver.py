"""Turning a graph into objects."""

from collections.abc import Callable
from typing import Any, TypeVar

from .errors import CircularDependencyError, MissingProviderError
from .graph import Graph, type_name
from .lifecycle import Lifecycle

T = TypeVar("T", bound=Any)


class Resolver:
    """Builds and caches the instances a graph describes.

    Every provider is a singleton: an instance is built once and reused. Resources
    register themselves with the lifecycle as they are created, which is what makes
    the shutdown order the reverse of the construction order.
    """

    def __init__(
        self,
        graph: Graph,
        lifecycle: Lifecycle,
        builtins: dict[Any, Callable[[], Any]],
    ) -> None:
        self._graph = graph
        self._lifecycle = lifecycle
        self._builtins = builtins
        self._instances: dict[Any, Any] = {}
        self._resolving: list[Any] = []

    async def resolve(self, type_: type[T]) -> T:
        """Produce an instance of the requested type."""
        if type_ in self._instances:
            return self._instances[type_]  # type: ignore[no-any-return]

        value = self._graph.values.get(type_)
        if value is not None:
            return value.value  # type: ignore[no-any-return]

        builtin = self._builtins.get(type_)
        if builtin is not None:
            self._instances[type_] = builtin()
            return self._instances[type_]  # type: ignore[no-any-return]

        if type_ in self._resolving:
            raise CircularDependencyError(
                self._resolving[self._resolving.index(type_) :], type_name
            )

        provider = self._graph.provider_for(type_)
        if provider is None:
            raise MissingProviderError(
                f"No provider registered for type {type_name(type_)}"
            )

        self._resolving.append(type_)
        try:
            instance = await self._build(provider)
        finally:
            self._resolving.pop()

        self._instances[type_] = instance
        return instance  # type: ignore[no-any-return]

    async def _build(self, provider: Any) -> Any:
        dependencies = [await self.resolve(dep) for dep in provider.dependencies]

        instance = provider.constructor(*dependencies)

        if hasattr(instance, "__await__"):
            instance = await instance

        if hasattr(instance, "__aiter__"):
            generator = instance
            instance = await anext(generator)
            self._lifecycle.add_resource(generator, name=provider.name)

        return instance

    def instances(self) -> dict[Any, Any]:
        """What has been built so far. For diagnostics."""
        return dict(self._instances)
