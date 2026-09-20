"""What an application is built from.

These are inert records: a Provide holds providers, a Component holds other
registrations, and none of them know how to run anything. Assembling them into a
graph is graph.flatten(), and running it is App.
"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from .annotate import As
from .errors import DuplicateProviderError

T = TypeVar("T", bound=Any)


@dataclass(frozen=True)
class Provider:
    """A constructor, the type it produces and the types it needs."""

    constructor: Callable[..., Any]
    return_type: Any
    dependencies: tuple[Any, ...] = ()

    @property
    def name(self) -> str:
        return str(getattr(self.constructor, "__name__", self.constructor))


@dataclass(frozen=True)
class Value:
    """An already-built object, registered under its own type."""

    type_: Any
    value: Any


@dataclass(frozen=True)
class Invokable:
    """A function to run at startup, and the types it needs."""

    func: Callable[..., Any]
    name: str
    dependencies: tuple[Any, ...] = ()


def dependencies_of(func: Callable[..., Any]) -> tuple[Any, ...]:
    """The parameter annotations of a constructor or invokable, in order."""
    dependencies = []
    for parameter_name, parameter in inspect.signature(func).parameters.items():
        if parameter_name == "self":
            continue
        if parameter.annotation is inspect.Signature.empty:
            raise ValueError(
                f"Parameter {parameter_name} in {func.__name__} must have a "
                f"type annotation"
            )
        dependencies.append(parameter.annotation)
    return tuple(dependencies)


def _return_type_of(constructor: Callable[..., Any]) -> Any:
    return_annotation = inspect.signature(constructor).return_annotation
    if return_annotation is inspect.Signature.empty:
        raise ValueError(
            f"Constructor {constructor.__name__} must have a return type annotation"
        )
    return return_annotation


@dataclass
class Provide:
    """Constructors to register, keyed by their return type."""

    providers: dict[Any, Provider] = field(default_factory=dict)

    def __init__(self, *constructors: Any) -> None:
        self.providers = {}
        for constructor in constructors:
            self._register_constructor(constructor)

    def _register_constructor(self, constructor: Any) -> None:
        annotations: list[As] = []
        if isinstance(constructor, tuple) and len(constructor) == 2:
            candidate, candidate_annotations = constructor
            if callable(candidate) and isinstance(candidate_annotations, list):
                constructor, annotations = candidate, candidate_annotations

        dependencies = dependencies_of(constructor)
        return_type = _return_type_of(constructor)
        self._add(Provider(constructor, return_type, dependencies))

        for inner_type in _resource_inner_types(return_type):
            self._add(Provider(constructor, inner_type, dependencies))

        for annotation in annotations:
            if isinstance(annotation, As):
                self._add(
                    Provider(constructor, annotation.interface_type, dependencies)
                )

    def _add(self, provider: Provider) -> None:
        existing = self.providers.get(provider.return_type)
        if existing is not None and existing.constructor is not provider.constructor:
            from .graph import type_name

            raise DuplicateProviderError(
                type_name(provider.return_type), existing.name, provider.name
            )
        self.providers[provider.return_type] = provider

    def __iter__(self) -> Any:
        return iter(self.providers.values())

    def __len__(self) -> int:
        return len(self.providers)

    def __contains__(self, type_: Any) -> bool:
        return type_ in self.providers

    def __getitem__(self, type_: Any) -> Provider:
        if type_ not in self.providers:
            raise KeyError(f"No provider registered for type {type_}")
        return self.providers[type_]


def _resource_inner_types(return_type: Any) -> tuple[Any, ...]:
    """The T behind an AsyncIterator[T], if that is what this is.

    Only the iterator family: unwrapping every generic would make
    Annotated[str, "server"] claim plain str as well, which is the opposite of
    why that alias exists.
    """
    from collections.abc import (
        AsyncGenerator,
        AsyncIterable,
        AsyncIterator,
        Generator,
        Iterable,
        Iterator,
    )
    from typing import Any as AnyType
    from typing import get_origin

    resource_origins = (
        AsyncIterator,
        AsyncIterable,
        AsyncGenerator,
        Iterator,
        Iterable,
        Generator,
    )
    if get_origin(return_type) not in resource_origins:
        return ()
    args = getattr(return_type, "__args__", ())
    if not args or args[0] is AnyType:
        return ()
    return (args[0],)


@dataclass
class Supply:
    """Values to register, keyed by their own type."""

    values: dict[Any, Value] = field(default_factory=dict)

    def __init__(self, *values: Any) -> None:
        self.values = {}
        for value in values:
            if isinstance(value, Value):
                self.values[value.type_] = value
            else:
                self.values[type(value)] = Value(type(value), value)

    def __iter__(self) -> Any:
        return iter(self.values.values())

    def __len__(self) -> int:
        return len(self.values)

    def __contains__(self, type_: Any) -> bool:
        return type_ in self.values

    def __getitem__(self, type_: Any) -> Any:
        if type_ not in self.values:
            raise KeyError(f"No value registered for type {type_}")
        return self.values[type_].value


@dataclass
class Invoke:
    """Functions to run at startup. These are the roots of the graph."""

    invokables: list[Invokable] = field(default_factory=list)

    def __init__(self, *functions: Callable[..., Any]) -> None:
        self.invokables = [
            Invokable(function, function.__name__, dependencies_of(function))
            for function in functions
        ]

    def __iter__(self) -> Any:
        return iter(self.invokables)

    def __len__(self) -> int:
        return len(self.invokables)


@dataclass
class Component:
    """A named group of registrations. Components nest to any depth."""

    name: str | None = None
    children: tuple[Any, ...] = ()

    def __init__(self, *registrations: Any, name: str | None = None) -> None:
        if registrations and isinstance(registrations[0], str):
            name = registrations[0]
            registrations = registrations[1:]
        self.name = name
        self.children = tuple(registrations)

    def __iter__(self) -> Any:
        return iter(self.children)

    def __len__(self) -> int:
        return len(self.children)
