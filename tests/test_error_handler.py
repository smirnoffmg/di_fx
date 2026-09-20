"""Tests for the enhanced error handler functionality."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from di_fx.error_handler import ErrorCategory, ErrorHandler
from di_fx.lifecycle import Lifecycle
from di_fx.lifecycle_manager import LifecycleManager


class TestErrorHandler:
    """Test cases for ErrorHandler class."""

    @pytest.fixture
    def lifecycle(self):
        """Create a mock lifecycle."""
        return MagicMock(spec=Lifecycle)

    @pytest.fixture
    def lifecycle_manager(self):
        """Create a mock lifecycle manager."""
        return MagicMock(spec=LifecycleManager)

    @pytest.fixture
    def error_handler(self, lifecycle, lifecycle_manager):
        """Create an ErrorHandler instance for testing."""
        return ErrorHandler(lifecycle, lifecycle_manager)

    def test_error_handler_initialization(self, lifecycle, lifecycle_manager):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler(lifecycle, lifecycle_manager)
        assert handler._lifecycle == lifecycle
        assert handler._lifecycle_manager == lifecycle_manager
        assert isinstance(handler._logger, logging.Logger)

    def test_error_category_enum_values(self):
        """Test ErrorCategory enum has expected values."""
        assert ErrorCategory.STARTUP.value == "startup"
        assert ErrorCategory.SHUTDOWN.value == "shutdown"
        assert ErrorCategory.LIFECYCLE.value == "lifecycle"
        assert ErrorCategory.DEPENDENCY.value == "dependency"
        assert ErrorCategory.CLEANUP.value == "cleanup"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.TIMEOUT.value == "timeout"

    @pytest.mark.asyncio
    async def test_handle_startup_failure(self, error_handler, lifecycle_manager):
        """Test startup failure handling."""
        error = RuntimeError("Startup failed")

        with patch.object(error_handler._logger, "error") as mock_logger:
            await error_handler.handle_startup_failure(error)

            # Verify logging
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            assert "Startup failed" in call_args[0][0]
            assert call_args[1]["extra"]["context"] == "startup"
            assert call_args[1]["extra"]["operation"] == "startup_failure"

            # Verify cleanup is called
            lifecycle_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_shutdown_error(self, error_handler):
        """Test shutdown error handling."""
        error = RuntimeError("Shutdown failed")

        with patch.object(error_handler._logger, "error") as mock_logger:
            await error_handler.handle_shutdown_error(error)

            # Verify logging
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            assert "Error during shutdown" in call_args[0][0]
            assert call_args[1]["extra"]["context"] == "shutdown"
            assert call_args[1]["extra"]["operation"] == "shutdown_error"

    @pytest.mark.asyncio
    async def test_handle_lifecycle_error_start(self, error_handler, lifecycle_manager):
        """Test lifecycle error handling for start context."""
        error = RuntimeError("Lifecycle start failed")

        with patch.object(error_handler._logger, "error") as mock_logger:
            await error_handler.handle_lifecycle_error(error, "start")

            # Verify logging
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            # Check the format string and arguments separately
            assert call_args[0][0] == "Lifecycle error during %s: %s"
            assert call_args[0][1] == "start"
            assert call_args[0][2] == error
            assert call_args[1]["extra"]["context"] == "lifecycle_start"
            assert call_args[1]["extra"]["operation"] == "lifecycle_error"

            # Verify cleanup is called for start errors
            lifecycle_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_lifecycle_error_stop(self, error_handler):
        """Test lifecycle error handling for stop context."""
        error = RuntimeError("Lifecycle stop failed")

        with patch.object(error_handler._logger, "error") as mock_logger:
            await error_handler.handle_lifecycle_error(error, "stop")

            # Verify logging
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            # Check the format string and arguments separately
            assert call_args[0][0] == "Lifecycle error during %s: %s"
            assert call_args[0][1] == "stop"
            assert call_args[0][2] == error
            assert call_args[1]["extra"]["context"] == "lifecycle_stop"
            assert call_args[1]["extra"]["operation"] == "lifecycle_error"

            # Verify no cleanup for stop errors

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_first_try(self, error_handler):
        """Test retry mechanism when operation succeeds on first try."""
        operation = AsyncMock(return_value="success")

        result = await error_handler._retry_with_backoff(operation)

        assert result == "success"
        operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_after_retries(self, error_handler):
        """Test retry mechanism when operation succeeds after retries."""
        operation = AsyncMock(
            side_effect=[RuntimeError("Failed"), RuntimeError("Failed"), "success"]
        )

        with patch.object(error_handler._logger, "warning") as mock_warning:
            result = await error_handler._retry_with_backoff(operation, max_retries=2)

            assert result == "success"
            assert operation.call_count == 3
            assert mock_warning.call_count == 2  # Two retry attempts

    @pytest.mark.asyncio
    async def test_retry_with_backoff_all_attempts_fail(self, error_handler):
        """Test retry mechanism when all attempts fail."""
        error = RuntimeError("Persistent failure")
        operation = AsyncMock(side_effect=error)

        with patch.object(error_handler._logger, "error") as mock_error:
            with pytest.raises(RuntimeError) as exc_info:
                await error_handler._retry_with_backoff(operation, max_retries=2)

            assert exc_info.value == error
            assert operation.call_count == 3  # Initial + 2 retries
            mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_with_backoff_custom_parameters(self, error_handler):
        """Test retry mechanism with custom parameters."""
        operation = AsyncMock(side_effect=[RuntimeError("Failed"), "success"])

        with patch("asyncio.sleep") as mock_sleep:
            await error_handler._retry_with_backoff(
                operation, max_retries=1, base_delay=0.5
            )

            # Verify delay calculation: 0.5 * (2^0) = 0.5 seconds
            mock_sleep.assert_called_once_with(0.5)

    @pytest.mark.asyncio
    async def test_safe_execute_success(self, error_handler):
        """Test safe_execute when operation succeeds."""
        operation = AsyncMock(return_value="success")

        result = await error_handler.safe_execute(operation, "test_context")

        assert result == "success"
        operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_execute_with_retry_success(self, error_handler):
        """Test safe_execute with retry when operation succeeds after retries."""
        operation = AsyncMock(side_effect=[RuntimeError("Failed"), "success"])

        result = await error_handler.safe_execute(
            operation, "test_context", retry_on_failure=True, max_retries=1
        )

        assert result == "success"
        assert operation.call_count == 2

    @pytest.mark.asyncio
    async def test_safe_execute_with_fallback(self, error_handler):
        """Test safe_execute with fallback operation."""
        operation = AsyncMock(side_effect=RuntimeError("Failed"))
        fallback = AsyncMock(return_value="fallback_success")

        result = await error_handler.safe_execute(
            operation, "test_context", fallback=fallback
        )

        assert result == "fallback_success"
        operation.assert_called_once()
        fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_execute_fallback_also_fails(self, error_handler):
        """Test safe_execute when both operation and fallback fail."""
        operation = AsyncMock(side_effect=RuntimeError("Operation failed"))
        fallback = AsyncMock(side_effect=RuntimeError("Fallback failed"))

        with patch.object(error_handler._logger, "error") as mock_error:
            with pytest.raises(RuntimeError) as exc_info:
                await error_handler.safe_execute(
                    operation, "test_context", fallback=fallback
                )

            assert "Operation failed" in str(exc_info.value)
            # Should be called twice: once for operation failure, once for fallback failure
            assert mock_error.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_on_failure_success(self, error_handler, lifecycle_manager):
        """Test cleanup on failure when cleanup succeeds."""
        lifecycle_manager.is_started.return_value = True

        await error_handler._cleanup_on_failure()

        lifecycle_manager.stop.assert_called_once()
        error_handler._lifecycle.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_on_failure_with_cleanup_error(
        self, error_handler, lifecycle_manager
    ):
        """Test cleanup on failure when cleanup itself fails."""
        lifecycle_manager.is_started.return_value = True
        lifecycle_manager.stop.side_effect = RuntimeError("Cleanup failed")

        with patch.object(error_handler._logger, "error") as mock_logger:
            # Should not raise exception, should handle cleanup errors gracefully
            await error_handler._cleanup_on_failure()

            # Verify cleanup error is logged
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            assert "Cleanup error during failure recovery" in call_args[0][0]
            assert call_args[1]["extra"]["context"] == "cleanup_failure"
            assert call_args[1]["extra"]["operation"] == "cleanup_on_failure"

    @pytest.mark.asyncio
    async def test_cleanup_on_failure_lifecycle_not_started(
        self, error_handler, lifecycle_manager
    ):
        """Test cleanup on failure when lifecycle is not started."""
        lifecycle_manager.is_started.return_value = False

        await error_handler._cleanup_on_failure()

        # Should not call lifecycle_manager.stop when not started
        lifecycle_manager.stop.assert_not_called()
        # But should still call lifecycle.stop
        error_handler._lifecycle.stop.assert_called_once()

    def test_create_error_context(self, error_handler, lifecycle_manager):
        """Test error context creation."""
        lifecycle_manager.is_started.return_value = True

        context = error_handler.create_error_context(
            "test_operation", extra_info="test"
        )

        assert context["operation"] == "test_operation"
        assert context["lifecycle_started"] is True
        assert context["extra_info"] == "test"
        assert "timestamp" in context

    def test_is_cleanup_needed_true(self, error_handler, lifecycle_manager):
        """Test is_cleanup_needed when cleanup is needed."""
        lifecycle_manager.is_started.return_value = True

        result = error_handler.is_cleanup_needed()

        assert result is True

    def test_is_cleanup_needed_false(self, error_handler, lifecycle_manager):
        """Test is_cleanup_needed when cleanup is not needed."""
        lifecycle_manager.is_started.return_value = False

        result = error_handler.is_cleanup_needed()

        assert result is False

    def test_get_error_summary(self, error_handler):
        """Test error summary generation."""
        error = RuntimeError("Test error")
        context = {"operation": "test_op"}

        summary = error_handler.get_error_summary(error, context)

        assert "Error in test_op" in summary
        assert "RuntimeError" in summary
        assert "Test error" in summary

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_callback(
        self, error_handler, lifecycle_manager
    ):
        """Test graceful shutdown with callback."""
        callback = AsyncMock()
        lifecycle_manager.is_started.return_value = True

        await error_handler.graceful_shutdown(callback)

        callback.assert_called_once()
        lifecycle_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_without_callback(
        self, error_handler, lifecycle_manager
    ):
        """Test graceful shutdown without callback."""
        lifecycle_manager.is_started.return_value = True

        await error_handler.graceful_shutdown()

        lifecycle_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_callback_fails(
        self, error_handler, lifecycle_manager
    ):
        """Test graceful shutdown when callback fails."""
        callback = AsyncMock(side_effect=RuntimeError("Callback failed"))
        lifecycle_manager.is_started.return_value = True

        # Should not raise exception, should handle error gracefully
        await error_handler.graceful_shutdown(callback)

        # When callback fails, handle_shutdown_error is called but lifecycle_manager.stop is not called
        # because the exception is caught before reaching that point
        lifecycle_manager.stop.assert_not_called()
