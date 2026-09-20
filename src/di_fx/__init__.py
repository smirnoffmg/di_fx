"""
Dependency injection and application lifecycle for asyncio, inspired by Uber-Fx.

Build an application from constructor functions, start it in dependency order and
shut it down in reverse.
"""

__version__ = "0.4.0"
__author__ = "di_fx contributors"

from .annotate import Annotate, As
from .app import App
from .dotgraph import DotGraph
from .errors import (
    CircularDependencyError,
    DiFxError,
    DuplicateProviderError,
    HookTimeoutError,
    LifecycleError,
    MissingProviderError,
    ValidationError,
)
from .lifecycle import Hook, Lifecycle
from .named import Named
from .registrations import Component, Invoke, Provide, Supply
from .shutdowner import Shutdowner

__all__ = [
    "Annotate",
    "App",
    "As",
    "CircularDependencyError",
    "Component",
    "DiFxError",
    "DotGraph",
    "DuplicateProviderError",
    "Hook",
    "HookTimeoutError",
    "Invoke",
    "Lifecycle",
    "LifecycleError",
    "MissingProviderError",
    "Named",
    "Provide",
    "Shutdowner",
    "Supply",
    "ValidationError",
]
