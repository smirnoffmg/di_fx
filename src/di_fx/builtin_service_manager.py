"""
Built-in service management for dependency injection framework.

This module provides a BuiltinServiceManager class that handles all
built-in service concerns, separating them from the main App class.
"""

from typing import Any

from .dotgraph import DotGraph
from .shutdowner import Shutdowner


class BuiltinServiceManager:
    """Manages built-in services like DotGraph and Shutdowner."""

    def __init__(self) -> None:
        """Initialize the built-in service manager."""
        self._dotgraph: DotGraph | None = None
        self._shutdowner: Shutdowner | None = None
        self._shutdown_callback: Any | None = None

    def set_shutdown_callback(self, callback: Any) -> None:
        """Set the shutdown callback for the Shutdowner service."""
        self._shutdown_callback = callback

    def get_dotgraph(
        self, providers: dict[type[Any], Any], values: dict[type[Any], Any]
    ) -> DotGraph:
        """Get or create the DotGraph instance."""
        if self._dotgraph is None:
            self._dotgraph = DotGraph(providers, values)
        return self._dotgraph

    def get_shutdowner(self) -> Shutdowner:
        """Get or create the Shutdowner instance.

        The callback is looked up when shutdown is requested, not when the
        Shutdowner is built: a service can be resolved before the application
        has wired its callback up, and it must still shut the application down.
        """
        if self._shutdowner is None:
            self._shutdowner = Shutdowner(self._request_shutdown)
        return self._shutdowner

    def _request_shutdown(self) -> None:
        if self._shutdown_callback is not None:
            self._shutdown_callback()

    def is_dotgraph_initialized(self) -> bool:
        """Check if DotGraph has been initialized."""
        return self._dotgraph is not None

    def is_shutdowner_initialized(self) -> bool:
        """Check if Shutdowner has been initialized."""
        return self._shutdowner is not None

    def reset(self) -> None:
        """Reset all built-in services (useful for testing)."""
        self._dotgraph = None
        self._shutdowner = None
