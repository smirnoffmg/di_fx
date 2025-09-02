"""
Programmatic shutdown functionality for di_fx.

This module provides the Shutdowner class that allows any part
of the application to trigger a graceful shutdown.
"""

from collections.abc import Callable


class Shutdowner:
    """Allows programmatic shutdown of the application.

    This is automatically provided by di_fx to any function that requests it.
    Similar to Uber-Fx's fx.Shutdowner.
    """

    def __init__(self, shutdown_callback: Callable[[], None]):
        """Initialize the shutdowner.

        Args:
            shutdown_callback: Function to call when shutdown is requested
        """
        self._shutdown_callback = shutdown_callback
        self._shutdown_requested = False

    async def shutdown(self, reason: str | None = None) -> None:
        """Request a graceful shutdown of the application.

        Args:
            reason: Optional reason for the shutdown
        """
        if self._shutdown_requested:
            return  # Already shutting down

        self._shutdown_requested = True

        if reason:
            print(f"Shutdown requested: {reason}")
        else:
            print("Shutdown requested")

        # Call the shutdown callback
        self._shutdown_callback()

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested.

        Returns:
            True if shutdown has been requested
        """
        return self._shutdown_requested

    def __repr__(self) -> str:
        """String representation."""
        status = "shutting_down" if self._shutdown_requested else "active"
        return f"Shutdowner({status})"
