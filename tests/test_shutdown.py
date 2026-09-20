"""Shutdown behaviour: task cancellation, hook timeouts, rollback, error reporting."""

import asyncio
from collections.abc import AsyncIterator

import pytest

from di_fx import Component, Hook, Invoke, Lifecycle, Provide
from di_fx.lifecycle import HookTimeoutError
from di_fx.lifecycle_manager import LifecycleManager


class TestTaskCancellation:
    async def test_stop_cancels_tracked_tasks(self):
        manager = LifecycleManager()
        manager.set_loop(asyncio.get_running_loop())
        manager.start()

        for _ in range(4):
            manager.create_task(asyncio.sleep(100))

        await manager.stop()

        assert manager.get_task_count() == 0


class TestHookTimeout:
    async def test_slow_start_hook_times_out(self):
        lifecycle = Lifecycle()

        async def never_finishes() -> None:
            await asyncio.sleep(10)

        lifecycle.append(Hook(on_start=never_finishes, timeout=0.05, name="slow"))

        with pytest.raises(HookTimeoutError, match="slow"):
            await lifecycle.start()

    async def test_slow_stop_hook_times_out(self):
        lifecycle = Lifecycle()

        async def never_finishes() -> None:
            await asyncio.sleep(10)

        lifecycle.append(Hook(on_stop=never_finishes, timeout=0.05, name="slow"))
        await lifecycle.start()

        with pytest.raises(ExceptionGroup) as exc_info:
            await lifecycle.stop()

        assert isinstance(exc_info.value.exceptions[0], HookTimeoutError)


class TestRollback:
    async def test_failed_start_stops_only_started_hooks(self):
        lifecycle = Lifecycle()
        events: list[str] = []

        def hook(name: str, *, fails: bool = False) -> Hook:
            async def on_start() -> None:
                events.append(f"start:{name}")
                if fails:
                    raise RuntimeError(f"{name} refused to start")

            async def on_stop() -> None:
                events.append(f"stop:{name}")

            return Hook(on_start=on_start, on_stop=on_stop, name=name)

        lifecycle.append(hook("a"))
        lifecycle.append(hook("b"))
        lifecycle.append(hook("c", fails=True))
        lifecycle.append(hook("d"))

        with pytest.raises(RuntimeError, match="c refused to start"):
            await lifecycle.start()

        assert events == ["start:a", "start:b", "start:c", "stop:b", "stop:a"]

    async def test_stop_without_start_runs_nothing(self):
        lifecycle = Lifecycle()
        stopped = False

        async def on_stop() -> None:
            nonlocal stopped
            stopped = True

        lifecycle.append(Hook(on_stop=on_stop))
        await lifecycle.stop()

        assert not stopped


class TestResources:
    async def test_generator_provider_is_closed_when_startup_fails(self):
        closed = False

        async def new_connection() -> AsyncIterator[str]:
            nonlocal closed
            try:
                yield "connection"
            finally:
                closed = True

        def boom(connection: str) -> None:
            raise RuntimeError("invokable failed")

        app = Component(Provide(new_connection), Invoke(boom))

        with pytest.raises(RuntimeError, match="invokable failed"):
            await app.start()

        assert closed, "the resource created during initialization was left open"

    async def test_resources_and_hooks_close_in_one_reverse_order(self):
        events: list[str] = []

        async def new_connection() -> AsyncIterator[str]:
            events.append("open:connection")
            yield "connection"
            events.append("close:connection")

        def new_worker(connection: str, lifecycle: Lifecycle) -> int:
            async def on_stop() -> None:
                events.append("stop:worker")

            lifecycle.append(Hook(on_stop=on_stop, name="worker"))
            return 1

        def use(worker: int) -> None:
            pass

        app = Component(Provide(new_connection, new_worker), Invoke(use))
        await app.start()
        await app.stop()

        assert events == ["open:connection", "stop:worker", "close:connection"]


class TestErrorReporting:
    async def test_shutdown_errors_are_raised_not_swallowed(self):
        lifecycle = Lifecycle()

        async def bad_stop() -> None:
            raise RuntimeError("cleanup exploded")

        lifecycle.append(Hook(on_stop=bad_stop))
        await lifecycle.start()

        with pytest.raises(ExceptionGroup) as exc_info:
            await lifecycle.stop()

        assert "cleanup exploded" in str(exc_info.value.exceptions[0])

    async def test_every_stop_hook_runs_even_if_one_fails(self):
        lifecycle = Lifecycle()
        events: list[str] = []

        async def bad_stop() -> None:
            raise RuntimeError("boom")

        async def good_stop() -> None:
            events.append("good")

        lifecycle.append(Hook(on_stop=good_stop))
        lifecycle.append(Hook(on_stop=bad_stop))
        await lifecycle.start()

        with pytest.raises(ExceptionGroup):
            await lifecycle.stop()

        assert events == ["good"]


class TestApplicationShutdown:
    async def test_app_stop_reports_failures(self):
        def new_worker(lifecycle: Lifecycle) -> int:
            async def on_stop() -> None:
                raise RuntimeError("worker refused to stop")

            lifecycle.append(Hook(on_stop=on_stop))
            return 1

        def use(worker: int) -> None:
            pass

        app = Component(Provide(new_worker), Invoke(use))
        await app.start()

        with pytest.raises(ExceptionGroup) as exc_info:
            await app.stop()

        assert "worker refused to stop" in str(exc_info.value.exceptions[0])
