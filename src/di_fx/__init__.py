"""
Modern, async-first dependency injection for Python inspired by Uber-Fx.

This package provides a function-centric, event-loop native dependency
injection framework with superior performance and seamless async integration.
"""

__version__ = "0.1.0"
__author__ = "di_fx contributors"

from typing import Annotated

from .annotate import Annotate, As
from .app_orchestrator import AppOrchestrator
from .builtin_service_manager import BuiltinServiceManager
from .component import Component
from .component_processor import ComponentProcessor
from .component_processor_manager import ComponentProcessorManager
from .dependency_resolver import DependencyResolver
from .dotgraph import DotGraph
from .error_handler import ErrorHandler
from .invokable_executor import InvokableExecutor
from .invoke import Invoke
from .lifecycle import Hook, Lifecycle
from .lifecycle_manager import LifecycleManager
from .named import Named
from .provide import Provide
from .shutdowner import Shutdowner
from .state_manager import StateManager
from .supply import Supply
from .validation import ValidationError
from .validation_manager import ValidationManager

__all__ = [
    "Annotate",
    "Annotated",
    "As",
    "AppOrchestrator",
    "BuiltinServiceManager",
    "Component",
    "ComponentProcessor",
    "ComponentProcessorManager",
    "DependencyResolver",
    "ErrorHandler",
    "Invoke",
    "InvokableExecutor",
    "Named",
    "Provide",
    "Supply",
    "Lifecycle",
    "Hook",
    "LifecycleManager",
    "StateManager",
    "ValidationError",
    "ValidationManager",
    "DotGraph",
    "Shutdowner",
]
