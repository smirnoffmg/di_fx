"""Running an application: programmatic shutdown, signals, and exiting promptly."""

import asyncio
import os
import signal
import sys
import time

import pytest

from di_fx import Component, Invoke, Provide, Shutdowner


class Service:
    def __init__(self, shutdowner: Shutdowner) -> None:
        self.shutdowner = shutdowner


def new_service(shutdowner: Shutdowner) -> Service:
    return Service(shutdowner)


class TestProgrammaticShutdown:
    async def test_injected_shutdowner_stops_the_application(self):
        def use(service: Service) -> None:
            asyncio.get_running_loop().call_later(
                0.01, lambda: asyncio.ensure_future(service.shutdowner.shutdown())
            )

        app = Component(Provide(new_service), Invoke(use))

        await asyncio.wait_for(app.run(), timeout=2)

        assert not app.is_running()

    async def test_the_injected_shutdowner_is_the_one_the_app_listens_to(self):
        resolved: list[Service] = []

        def use(service: Service) -> None:
            resolved.append(service)

        app = Component(Provide(new_service), Invoke(use))
        await app.start()
        try:
            shutdowner = resolved[0].shutdowner
            # A no-op callback here is the bug this guards: the resolver used to
            # build its own Shutdowner, separate from the one the app wires up.
            assert shutdowner._shutdown_callback is not None
            await shutdowner.shutdown("test")
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not app.is_running()
        finally:
            await app.stop()

    async def test_run_exits_promptly(self):
        def use(service: Service) -> None:
            asyncio.get_running_loop().call_soon(
                lambda: asyncio.ensure_future(service.shutdowner.shutdown())
            )

        app = Component(Provide(new_service), Invoke(use))

        started = time.monotonic()
        await asyncio.wait_for(app.run(), timeout=2)
        elapsed = time.monotonic() - started

        # The old implementation polled is_running() every 100ms.
        assert elapsed < 0.05, f"took {elapsed:.3f}s to notice the shutdown request"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals only")
class TestSignals:
    async def test_sigterm_stops_the_application(self):
        def use(service: Service) -> None:
            asyncio.get_running_loop().call_later(
                0.01, lambda: os.kill(os.getpid(), signal.SIGTERM)
            )

        app = Component(Provide(new_service), Invoke(use))

        # If the application fails to install its own handler, the default action
        # for SIGTERM kills the test runner outright. This placeholder turns that
        # into an ordinary timeout failure.
        previous = signal.signal(signal.SIGTERM, lambda *_: None)
        try:
            await asyncio.wait_for(app.run(), timeout=2)
        finally:
            signal.signal(signal.SIGTERM, previous)

        assert not app.is_running()

    async def test_signal_handlers_are_removed_afterwards(self):
        def use(service: Service) -> None:
            asyncio.get_running_loop().call_soon(
                lambda: asyncio.ensure_future(service.shutdowner.shutdown())
            )

        app = Component(Provide(new_service), Invoke(use))
        await asyncio.wait_for(app.run(), timeout=2)

        # Leaving handlers installed would make the next SIGINT in this process
        # silently do nothing instead of raising KeyboardInterrupt.
        assert signal.getsignal(signal.SIGINT) is not None
