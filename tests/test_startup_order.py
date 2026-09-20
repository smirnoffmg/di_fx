"""Startup and shutdown phase ordering.

Constructors run during initialization, so the hooks they append must still be
accepted; the hooks themselves run afterwards, during execution. Getting these
two phases the wrong way round makes the documented pattern -- a provider that
appends a Hook for the resource it builds -- impossible to express.
"""

from di_fx import App, Hook, Invoke, Lifecycle, Provide


class Server:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


class TestStartupOrder:
    async def test_provider_can_append_hook_during_resolution(self):
        def new_server(lifecycle: Lifecycle) -> Server:
            server = Server()
            lifecycle.append(Hook(on_start=server.start, on_stop=server.stop))
            return server

        resolved: list[Server] = []

        def use_server(server: Server) -> None:
            resolved.append(server)

        app = App(Provide(new_server), Invoke(use_server))
        await app.start()

        assert resolved, "the invokable never ran"
        server = resolved[0]
        assert server.started
        assert not server.stopped

        await app.stop()
        assert server.stopped

    async def test_invokable_runs_before_startup_hooks(self):
        events: list[str] = []

        def new_server(lifecycle: Lifecycle) -> Server:
            events.append("construct")
            server = Server()

            async def on_start() -> None:
                events.append("start")

            lifecycle.append(Hook(on_start=on_start))
            return server

        def use_server(server: Server) -> None:
            events.append("invoke")

        app = App(Provide(new_server), Invoke(use_server))
        await app.start()
        await app.stop()

        assert events == ["construct", "invoke", "start"]

    async def test_hooks_stop_in_reverse_order(self):
        events: list[str] = []

        def hook(name: str) -> Hook:
            async def on_start() -> None:
                events.append(f"start:{name}")

            async def on_stop() -> None:
                events.append(f"stop:{name}")

            return Hook(on_start=on_start, on_stop=on_stop, name=name)

        def new_server(lifecycle: Lifecycle) -> Server:
            lifecycle.append(hook("first"))
            lifecycle.append(hook("second"))
            return Server()

        def use_server(server: Server) -> None:
            pass

        app = App(Provide(new_server), Invoke(use_server))
        await app.start()
        await app.stop()

        assert events == [
            "start:first",
            "start:second",
            "stop:second",
            "stop:first",
        ]
