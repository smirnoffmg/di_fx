"""
Modern, async-first dependency injection for Python inspired by Uber-Fx.

This package provides a function-centric, event-loop native dependency
injection framework with superior performance and seamless async integration.
"""

__version__ = "0.1.0"
__author__ = "di_fx contributors"

from typing import Annotated

from .annotate import Annotate, As
from .app import App
from .dotgraph import DotGraph
from .invoke import Invoke
from .lifecycle import Hook, Lifecycle
from .module import Module
from .named import Named
from .options import Options
from .provide import Provide
from .shutdowner import Shutdowner
from .supply import Supply
from .validation import ValidationError

__all__ = [
    "Annotate",
    "Annotated",
    "As",
    "App",
    "Invoke",
    "Module",
    "Named",
    "Options",
    "Provide",
    "Supply",
    "Lifecycle",
    "Hook",
    "ValidationError",
    "DotGraph",
    "Shutdowner",
]
