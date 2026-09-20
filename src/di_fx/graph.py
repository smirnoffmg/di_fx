"""The immutable dependency graph, and the rules for reading it.

One structure owns providers, values and invokables; one predicate says whether a
dependency can be satisfied. The resolver and the validator both use that
predicate, so they cannot disagree about what a valid graph is.
"""

from dataclasses import dataclass, field
from typing import Any

from .dotgraph import DotGraph
from .errors import CircularDependencyError, DuplicateProviderError, ValidationError
from .lifecycle import Lifecycle
from .named import get_named_type_info, is_named_type
from .registrations import (
    Component,
    Invokable,
    Invoke,
    Provide,
    Provider,
    Supply,
    Value,
)
from .shutdowner import Shutdowner

#: Types the resolver supplies on its own, without a registered provider.
BUILTIN_TYPES: tuple[Any, ...] = (Lifecycle, DotGraph, Shutdowner)


def type_name(type_: Any) -> str:
    """Render a dependency key the way a user wrote it."""
    named = get_named_type_info(type_)
    if named is not None:
        name, base_type = named
        return f"{name}:{base_type.__name__}"
    return str(getattr(type_, "__name__", type_))


@dataclass(frozen=True)
class Graph:
    """Everything an application was built from, flattened and indexed."""

    providers: dict[Any, Provider] = field(default_factory=dict)
    values: dict[Any, Value] = field(default_factory=dict)
    invokables: tuple[Invokable, ...] = ()

    def can_resolve(self, dep_type: Any) -> bool:
        """Whether the resolver would be able to produce this dependency."""
        if dep_type in self.providers or dep_type in self.values:
            return True
        if dep_type in BUILTIN_TYPES:
            return True
        if is_named_type(dep_type):
            named = get_named_type_info(dep_type)
            return named is not None and named[1] in self.providers
        return False

    def provider_for(self, type_: Any) -> Provider | None:
        """The provider for a type, falling back to the base type of a Named."""
        provider = self.providers.get(type_)
        if provider is not None:
            return provider
        if is_named_type(type_):
            named = get_named_type_info(type_)
            if named is not None:
                return self.providers.get(named[1])
        return None


def flatten(*registrations: Any) -> Graph:
    """Walk the registration tree into one graph."""
    providers: dict[Any, Provider] = {}
    values: dict[Any, Value] = {}
    invokables: list[Invokable] = []

    def visit(registration: Any) -> None:
        if isinstance(registration, Provide):
            for provider in registration:
                existing = providers.get(provider.return_type)
                if (
                    existing is not None
                    and existing.constructor is not provider.constructor
                ):
                    raise DuplicateProviderError(
                        type_name(provider.return_type), existing.name, provider.name
                    )
                providers[provider.return_type] = provider
        elif isinstance(registration, Supply):
            for value in registration:
                values[value.type_] = value
        elif isinstance(registration, Invoke):
            invokables.extend(registration)
        elif isinstance(registration, Component):
            for child in registration:
                visit(child)
        else:
            raise ValueError(f"Unknown registration type: {type(registration)}")

    for registration in registrations:
        visit(registration)

    return Graph(providers, values, tuple(invokables))


def validate(graph: Graph) -> None:
    """Check that every dependency is satisfiable and no type depends on itself."""
    errors: list[str] = []

    for provider_type, provider in graph.providers.items():
        for dep_type in provider.dependencies:
            if not graph.can_resolve(dep_type):
                errors.append(
                    f"Provider {type_name(provider_type)} depends on "
                    f"{type_name(dep_type)}, but no provider is registered for "
                    f"{type_name(dep_type)}"
                )

    for invokable in graph.invokables:
        for dep_type in invokable.dependencies:
            if not graph.can_resolve(dep_type):
                errors.append(
                    f"Invokable {invokable.name} depends on {type_name(dep_type)}, "
                    f"but no provider is registered for {type_name(dep_type)}"
                )

    errors.extend(_cycle_errors(graph))

    if errors:
        raise ValidationError(f"Validation failed with {len(errors)} error(s):", errors)


def _cycle_errors(graph: Graph) -> list[str]:
    """Report every cycle once, naming only the types on it."""
    finished: set[Any] = set()
    seen: set[frozenset[Any]] = set()
    errors: list[str] = []

    for provider_type in graph.providers:
        for cycle in _find_cycles(provider_type, graph, finished, []):
            key = frozenset(cycle)
            if key in seen:
                continue
            seen.add(key)
            errors.append(str(CircularDependencyError(cycle, type_name)))

    return errors


def _find_cycles(
    current_type: Any, graph: Graph, finished: set[Any], stack: list[Any]
) -> list[list[Any]]:
    if current_type in stack:
        # The cycle is the tail of the path, not the whole path: the types that
        # merely lead into it are not part of it.
        return [stack[stack.index(current_type) :]]

    if current_type in finished or current_type not in graph.providers:
        return []

    stack.append(current_type)
    cycles: list[list[Any]] = []
    for dep_type in graph.providers[current_type].dependencies:
        cycles.extend(_find_cycles(dep_type, graph, finished, stack))
    stack.pop()

    if not cycles:
        finished.add(current_type)
    return cycles
