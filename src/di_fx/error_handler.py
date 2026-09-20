"""
Error handling and recovery for dependency injection framework.

This module provides the ErrorHandler class that handles all error handling,
cleanup, and recovery logic, separating these concerns from orchestration.
"""

import asyncio
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any

from .lifecycle import Lifecycle
from .lifecycle_manager import LifecycleManager


class ErrorCategory(Enum):
    """Error categories for better error handling and recovery."""

    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    LIFECYCLE = "lifecycle"
    DEPENDENCY = "dependency"
    CLEANUP = "cleanup"
    VALIDATION = "validation"
    TIMEOUT = "timeout"


class ErrorHandler:
    """Handles error handling, cleanup, and recovery for the DI framework."""

    def __init__(
        self, lifecycle: Lifecycle, lifecycle_manager: LifecycleManager
    ) -> None:
        """Initialize the error handler with lifecycle components."""
        self._lifecycle = lifecycle
        self._lifecycle_manager = lifecycle_manager
        self._logger = logging.getLogger(__name__)

    async def _retry_with_backoff(
        self,
        operation: Callable[[], Any],
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> Any:
        """Retry an operation with exponential backoff."""
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except Exception as error:
                last_exception = error
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    self._logger.warning(
                        "Operation failed, retrying in %.2f seconds (attempt %d/%d): %s",
                        delay,
                        attempt + 1,
                        max_retries + 1,
                        error,
                    )
                    await asyncio.sleep(delay)
                else:
                    self._logger.error(
                        "Operation failed after %d attempts: %s", max_retries + 1, error
                    )

        if last_exception is None:
            raise RuntimeError("Unexpected error in retry mechanism")
        raise last_exception

    async def handle_startup_failure(self, error: Exception) -> None:
        """Handle errors that occur during application startup.

        Args:
            error: The exception that occurred during startup
        """
        self._logger.error(
            "Startup failed: %s",
            error,
            extra={"context": "startup", "operation": "startup_failure"},
        )
        await self._cleanup_on_failure()

    async def handle_shutdown_error(self, error: Exception) -> None:
        """Handle errors that occur during application shutdown.

        Args:
            error: The exception that occurred during shutdown
        """
        self._logger.error(
            "Error during shutdown: %s",
            error,
            extra={"context": "shutdown", "operation": "shutdown_error"},
        )
        # Continue with cleanup despite the error

    async def handle_lifecycle_error(self, error: Exception, context: str) -> None:
        """Handle errors that occur during lifecycle operations.

        Args:
            error: The exception that occurred
            context: Context where the error occurred (e.g., 'start', 'stop')
        """
        self._logger.error(
            "Lifecycle error during %s: %s",
            context,
            error,
            extra={"context": f"lifecycle_{context}", "operation": "lifecycle_error"},
        )
        if context == "start":
            await self._cleanup_on_failure()
        elif context == "stop":
            # For stop errors, we try to continue cleanup
            pass

    async def _cleanup_on_failure(self) -> None:
        """Cleanup resources when startup fails."""
        try:
            if self._lifecycle_manager.is_started():
                await self._lifecycle_manager.stop()
            await self._lifecycle.stop()
        except Exception as cleanup_error:
            # Log cleanup errors but don't re-raise them
            self._logger.error(
                "Cleanup error during failure recovery: %s",
                cleanup_error,
                extra={"context": "cleanup_failure", "operation": "cleanup_on_failure"},
            )

    async def safe_execute(
        self,
        operation: Callable[[], Any],
        context: str,
        fallback: Callable[[], Any] | None = None,
        retry_on_failure: bool = False,
        max_retries: int = 3,
    ) -> Any:
        """Safely execute an operation with error handling and optional retry.

        Args:
            operation: The operation to execute
            context: Context for error reporting
            fallback: Optional fallback operation if the main operation fails
            retry_on_failure: Whether to retry the operation on failure
            max_retries: Maximum number of retry attempts

        Returns:
            The result of the operation or fallback
        """
        try:
            if retry_on_failure:
                return await self._retry_with_backoff(operation, max_retries)
            else:
                return await operation()
        except Exception as error:
            await self.handle_lifecycle_error(error, context)
            if fallback:
                try:
                    return await fallback()
                except Exception as fallback_error:
                    self._logger.error(
                        "Fallback operation also failed: %s",
                        fallback_error,
                        extra={
                            "context": f"fallback_{context}",
                            "operation": "safe_execute",
                        },
                    )
            raise

    def create_error_context(
        self, operation_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Create a context object for error reporting.

        Args:
            operation_name: Name of the operation that failed
            **kwargs: Additional context information

        Returns:
            Error context dictionary
        """
        return {
            "operation": operation_name,
            "lifecycle_started": self._lifecycle_manager.is_started(),
            "timestamp": (
                asyncio.get_event_loop().time()
                if asyncio.get_event_loop().is_running()
                else None
            ),
            **kwargs,
        }

    async def graceful_shutdown(
        self, shutdown_callback: Callable[[], Any] | None = None
    ) -> None:
        """Perform a graceful shutdown with error handling.

        Args:
            shutdown_callback: Optional callback to execute during shutdown
        """
        try:
            if shutdown_callback:
                await shutdown_callback()

            # Stop lifecycle manager
            if self._lifecycle_manager.is_started():
                await self._lifecycle_manager.stop()

            # Stop lifecycle hooks
            await self._lifecycle.stop()

        except Exception as error:
            await self.handle_shutdown_error(error)

    def is_cleanup_needed(self) -> bool:
        """Check if cleanup is needed based on current state."""
        return self._lifecycle_manager.is_started()

    def get_error_summary(self, error: Exception, context: dict[str, Any]) -> str:
        """Generate a summary of an error for logging.

        Args:
            error: The exception that occurred
            context: Error context information

        Returns:
            Formatted error summary string
        """
        return f"Error in {context.get('operation', 'unknown')}: {type(error).__name__}: {error}"
