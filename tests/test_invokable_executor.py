"""Tests for the InvokableExecutor class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from di_fx.builtin_service_manager import BuiltinServiceManager
from di_fx.invokable_executor import InvokableExecutor
from di_fx.invoke import Invokable


class TestInvokableExecutor:
    """Test cases for InvokableExecutor class."""

    @pytest.fixture
    def builtin_service_manager(self):
        """Create a mock builtin service manager."""
        return MagicMock(spec=BuiltinServiceManager)

    @pytest.fixture
    def providers(self):
        """Create mock providers dictionary."""
        return {}

    @pytest.fixture
    def values(self):
        """Create mock values dictionary."""
        return {}

    @pytest.fixture
    def invokable_executor(self, builtin_service_manager, providers, values):
        """Create an InvokableExecutor instance for testing."""
        return InvokableExecutor(builtin_service_manager, providers, values)

    @pytest.fixture
    def mock_invokable(self):
        """Create a mock invokable."""
        invokable = MagicMock(spec=Invokable)
        invokable.name = "test_invokable"
        invokable.func = MagicMock()
        invokable.dependencies = []
        return invokable

    @pytest.fixture
    def mock_resolve_dependency(self):
        """Create a mock dependency resolver."""
        return AsyncMock()

    def test_initialization(self, builtin_service_manager, providers, values):
        """Test InvokableExecutor initialization."""
        executor = InvokableExecutor(builtin_service_manager, providers, values)

        assert executor._builtin_service_manager == builtin_service_manager
        assert executor._providers == providers
        assert executor._values == values

    @pytest.mark.asyncio
    async def test_execute_invokables_success(
        self, invokable_executor, mock_invokable, mock_resolve_dependency
    ):
        """Test successful execution of invokables."""
        invokables = [mock_invokable]

        with patch.object(
            invokable_executor, "_execute_single_invokable"
        ) as mock_execute:
            await invokable_executor.execute_invokables(
                invokables, mock_resolve_dependency
            )

            mock_execute.assert_called_once_with(
                mock_invokable, mock_resolve_dependency
            )

    @pytest.mark.asyncio
    async def test_execute_invokables_with_error(
        self, invokable_executor, mock_invokable, mock_resolve_dependency
    ):
        """Test execution when an invokable fails."""
        invokables = [mock_invokable]
        error = RuntimeError("Test error")

        with patch.object(
            invokable_executor, "_execute_single_invokable", side_effect=error
        ):
            with patch("builtins.print") as mock_print:
                with pytest.raises(RuntimeError):
                    await invokable_executor.execute_invokables(
                        invokables, mock_resolve_dependency
                    )

                mock_print.assert_called_once_with(
                    f"Error executing {mock_invokable.name}: {error}"
                )

    @pytest.mark.asyncio
    async def test_execute_single_invokable_no_dependencies(
        self, invokable_executor, mock_invokable, mock_resolve_dependency
    ):
        """Test executing a single invokable with no dependencies."""
        mock_invokable.dependencies = []
        mock_invokable.func.return_value = "result"

        await invokable_executor._execute_single_invokable(
            mock_invokable, mock_resolve_dependency
        )

        mock_invokable.func.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_execute_single_invokable_with_dependencies(
        self, invokable_executor, mock_invokable, mock_resolve_dependency
    ):
        """Test executing a single invokable with dependencies."""
        mock_invokable.dependencies = [str, int]
        mock_invokable.func.return_value = "result"
        resolved_deps = ["string", 42]

        with patch.object(
            invokable_executor,
            "_resolve_invokable_dependencies",
            return_value=resolved_deps,
        ):
            await invokable_executor._execute_single_invokable(
                mock_invokable, mock_resolve_dependency
            )

            mock_invokable.func.assert_called_once_with(*resolved_deps)

    @pytest.mark.asyncio
    async def test_execute_single_invokable_async_result(
        self, invokable_executor, mock_invokable, mock_resolve_dependency
    ):
        """Test executing a single invokable that returns an async result."""
        mock_invokable.dependencies = []

        # Create a proper async mock that can be awaited
        async def async_func():
            return "async_result"

        mock_invokable.func.return_value = async_func()

        await invokable_executor._execute_single_invokable(
            mock_invokable, mock_resolve_dependency
        )

        mock_invokable.func.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_resolve_invokable_dependencies_builtin_services(
        self, invokable_executor, mock_resolve_dependency
    ):
        """Test resolving dependencies for built-in services."""
        from di_fx.dotgraph import DotGraph
        from di_fx.shutdowner import Shutdowner

        dep_types = [DotGraph, Shutdowner]
        mock_dotgraph = MagicMock()
        mock_shutdowner = MagicMock()

        invokable_executor._builtin_service_manager.get_dotgraph.return_value = (
            mock_dotgraph
        )
        invokable_executor._builtin_service_manager.get_shutdowner.return_value = (
            mock_shutdowner
        )

        result = await invokable_executor._resolve_invokable_dependencies(
            dep_types, mock_resolve_dependency
        )

        assert result == [mock_dotgraph, mock_shutdowner]
        invokable_executor._builtin_service_manager.get_dotgraph.assert_called_once_with(
            invokable_executor._providers, invokable_executor._values
        )
        invokable_executor._builtin_service_manager.get_shutdowner.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_invokable_dependencies_custom_types(
        self, invokable_executor, mock_resolve_dependency
    ):
        """Test resolving dependencies for custom types."""
        dep_types = [str, int]
        mock_resolve_dependency.return_value = "resolved"

        result = await invokable_executor._resolve_invokable_dependencies(
            dep_types, mock_resolve_dependency
        )

        assert result == ["resolved", "resolved"]
        assert mock_resolve_dependency.call_count == 2
        mock_resolve_dependency.assert_any_call(str)
        mock_resolve_dependency.assert_any_call(int)

    @pytest.mark.asyncio
    async def test_resolve_invokable_dependencies_mixed_types(
        self, invokable_executor, mock_resolve_dependency
    ):
        """Test resolving dependencies with mixed built-in and custom types."""
        from di_fx.dotgraph import DotGraph

        dep_types = [DotGraph, str]
        mock_dotgraph = MagicMock()

        invokable_executor._builtin_service_manager.get_dotgraph.return_value = (
            mock_dotgraph
        )
        mock_resolve_dependency.return_value = "resolved"

        result = await invokable_executor._resolve_invokable_dependencies(
            dep_types, mock_resolve_dependency
        )

        assert result == [mock_dotgraph, "resolved"]
        invokable_executor._builtin_service_manager.get_dotgraph.assert_called_once()
        mock_resolve_dependency.assert_called_once_with(str)

    def test_get_invokable_count(self, invokable_executor):
        """Test getting invokable count."""
        invokables: list[MagicMock] = [MagicMock(), MagicMock(), MagicMock()]

        result = invokable_executor.get_invokable_count(invokables)

        assert result == 3

    def test_get_invokable_count_empty(self, invokable_executor):
        """Test getting invokable count for empty list."""
        invokables: list[MagicMock] = []

        result = invokable_executor.get_invokable_count(invokables)

        assert result == 0

    def test_has_invokables_true(self, invokable_executor):
        """Test has_invokables when there are invokables."""
        invokables: list[MagicMock] = [MagicMock()]

        result = invokable_executor.has_invokables(invokables)

        assert result is True

    def test_has_invokables_false(self, invokable_executor):
        """Test has_invokables when there are no invokables."""
        invokables: list[MagicMock] = []

        result = invokable_executor.has_invokables(invokables)

        assert result is False

    def test_has_invokables_none(self, invokable_executor):
        """Test has_invokables with None."""
        result = invokable_executor.has_invokables(None)

        assert result is False
