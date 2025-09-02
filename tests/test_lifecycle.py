"""Tests for Lifecycle and Hook classes."""

import pytest

from di_fx.lifecycle import Hook, Lifecycle


class TestHook:
    """Test the Hook class."""

    def test_hook_creation(self):
        """Test creating a hook with basic parameters."""

        async def start_func():
            pass

        async def stop_func():
            pass

        hook = Hook(
            on_start=start_func, on_stop=stop_func, timeout=60.0, name="test_hook"
        )

        assert hook.on_start == start_func
        assert hook.on_stop == stop_func
        assert hook.timeout == 60.0
        assert hook.name == "test_hook"

    def test_hook_auto_naming(self):
        """Test automatic hook naming from functions."""

        async def my_start_function():
            pass

        hook = Hook(on_start=my_start_function)
        assert hook.name == "my_start_function_hook"

        hook2 = Hook(on_stop=my_start_function)
        assert hook2.name == "my_start_function_hook"

    def test_hook_defaults(self):
        """Test hook default values."""
        hook = Hook()
        assert hook.on_start is None
        assert hook.on_stop is None
        assert hook.timeout == 30.0
        assert hook.name == "unnamed_hook"


class TestLifecycle:
    """Test the Lifecycle class."""

    @pytest.fixture
    def lifecycle(self):
        """Create a fresh lifecycle instance."""
        return Lifecycle()

    def test_lifecycle_initialization(self, lifecycle):
        """Test lifecycle initialization."""
        assert len(lifecycle) == 0
        assert not lifecycle._started
        assert not lifecycle._stopped

    def test_append_hook(self, lifecycle):
        """Test adding hooks to lifecycle."""
        hook = Hook()
        lifecycle.append(hook)

        assert len(lifecycle) == 1
        assert hook in lifecycle

    @pytest.mark.asyncio
    async def test_cannot_add_hook_after_start(self, lifecycle):
        """Test that hooks cannot be added after lifecycle starts."""

        async def start_func():
            pass

        await lifecycle.start()

        hook = Hook(on_start=start_func)
        with pytest.raises(
            RuntimeError, match="Cannot add hooks after lifecycle has started"
        ):
            lifecycle.append(hook)

    @pytest.mark.asyncio
    async def test_lifecycle_start(self, lifecycle):
        """Test lifecycle startup."""
        start_called = False

        async def start_func():
            nonlocal start_called
            start_called = True

        hook = Hook(on_start=start_func)
        lifecycle.append(hook)

        await lifecycle.start()

        assert lifecycle._started
        assert start_called

    @pytest.mark.asyncio
    async def test_lifecycle_stop(self, lifecycle):
        """Test lifecycle shutdown."""
        stop_called = False

        async def stop_func():
            nonlocal stop_called
            stop_called = True

        hook = Hook(on_stop=stop_func)
        lifecycle.append(hook)

        await lifecycle.stop()

        assert lifecycle._stopped
        assert stop_called

    @pytest.mark.asyncio
    async def test_lifecycle_stop_reverse_order(self, lifecycle):
        """Test that shutdown hooks run in reverse order."""
        execution_order = []

        async def stop1():
            execution_order.append(1)

        async def stop2():
            execution_order.append(2)

        async def stop3():
            execution_order.append(3)

        lifecycle.append(Hook(on_stop=stop1))
        lifecycle.append(Hook(on_stop=stop2))
        lifecycle.append(Hook(on_stop=stop3))

        await lifecycle.stop()

        # Should execute in reverse order: 3, 2, 1
        assert execution_order == [3, 2, 1]

    @pytest.mark.asyncio
    async def test_lifecycle_idempotent(self, lifecycle):
        """Test that start/stop are idempotent."""
        call_count = 0

        async def start_func():
            nonlocal call_count
            call_count += 1

        hook = Hook(on_start=start_func)
        lifecycle.append(hook)

        # Call start multiple times
        await lifecycle.start()
        await lifecycle.start()
        await lifecycle.start()

        assert lifecycle._started
        assert call_count == 1  # Should only be called once

        # Call stop multiple times
        await lifecycle.stop()
        await lifecycle.stop()
        await lifecycle.stop()

        assert lifecycle._stopped
