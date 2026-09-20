# di_fx

**Dependency injection and application lifecycle for asyncio, inspired by [Uber-Fx](https://github.com/uber-go/fx)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/smirnoffmg/di_fx/workflows/CI/badge.svg)](https://github.com/smirnoffmg/di_fx/actions)
[![Coverage](https://codecov.io/gh/smirnoffmg/di_fx/branch/main/graph/badge.svg)](https://codecov.io/gh/smirnoffmg/di_fx)

> **Alpha.** The API changes between 0.x releases. Not published to PyPI yet.

---

## What it is for

di_fx wires an asyncio application from constructor functions and then runs it:
starts what needs starting in dependency order, waits, and shuts everything down
in reverse — including the resources whose startup failed halfway through.

It is aimed at **asyncio applications with no web framework above them**: workers,
queue consumers, daemons, bots, schedulers. There the graph has to be wired *and*
the process has to be run, and nothing in the ecosystem does both — application
runners have no dependency graph, and dependency containers stop at teardown.

**Building a web service?** Use [dishka](https://github.com/reagento/dishka) with your
framework's own `lifespan`. It has scopes, integrations and a larger community, and
your framework already owns the startup/shutdown phase. di_fx has nothing to add there.

## Install

```bash
pip install di-fx      # not published yet; for now: pip install -e .
```

No runtime dependencies. Python 3.12+.

## Quick start

```python
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from di_fx import App, Hook, Invoke, Lifecycle, Provide, Supply


@dataclass
class Config:
    dsn: str = "postgresql://localhost/app"


class Database:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn


class Worker:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def start(self) -> None:
        print("worker started")

    async def stop(self) -> None:
        print("worker stopped")


# A resource: everything before the yield is startup, everything after is shutdown.
async def new_database(config: Config) -> AsyncIterator[Database]:
    database = Database(config.dsn)
    yield database
    print("connection closed")


# A plain constructor. Its parameters are its dependencies, by type.
def new_worker(database: Database, lifecycle: Lifecycle) -> Worker:
    worker = Worker(database)
    lifecycle.append(Hook(on_start=worker.start, on_stop=worker.stop))
    return worker


# Invoke is what pulls the graph into existence: nothing is constructed unless
# something asks for it.
def run(worker: Worker) -> None:
    print(f"running against {worker.database.dsn}")


async def main() -> None:
    app = App(
        Supply(Config()),
        Provide(new_database, new_worker),
        Invoke(run),
    )
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
```

`run()` starts the application, waits for a shutdown request, then stops it.
SIGINT and SIGTERM are handled for the duration of the run. `async with app:`
starts and stops it around a block, and `start()` and `stop()` are there if you
would rather drive the process yourself.

## The two phases

This is the whole model, and it is Fx's:

**Initialization** — `Invoke` functions run, calling the constructors they need,
which call the constructors *they* need, in dependency order. Constructors may
append lifecycle hooks; nothing has started yet. This is the only window in which
a hook can be registered, so anything that needs one belongs behind an `Invoke`
rather than a `resolve()` call after startup.

**Execution** — startup hooks run in the order they were appended. The application
waits. Then shutdown hooks and resources unwind in the reverse of that order, which
is reverse dependency order.

If a startup hook fails, only what actually started is rolled back, and the failure
is raised. If a shutdown step fails, the remaining steps still run and the failures
are raised together as an `ExceptionGroup`.

## Building blocks

| | |
|---|---|
| `Provide(f, g, ...)` | Register constructors. The return annotation is the key; the parameter annotations are the dependencies. |
| `Supply(value, ...)` | Register an already-built value under its own type. |
| `Invoke(f, ...)` | Functions to run at startup. These are the roots of the graph. |
| `Component(...)` | Group the above into a module. Components nest to any depth; a leading string names one: `Component("database", ...)`. A component is inert — it describes, it does not run. |
| `App(...)` | The runnable application, built from any of the above. `run()`, `start()`/`stop()`, `async with`, `resolve()`, `validate()`. |
| `Lifecycle` / `Hook` | Ask for `Lifecycle` in a constructor and append a `Hook(on_start=..., on_stop=...)`. Each hook has a `timeout` (30s by default) that is enforced. |
| `Named("primary", Database)` | Distinguish two providers of the same underlying type. |
| `Annotate(f, As(Interface))` | Also register a constructor under an interface type. |

Providers are keyed by their return type, so **two constructors returning the same
type is an error**, not a silent last-wins. Use distinct types, `Named`, or
`Annotated[str, "tag"]` when the underlying type is something as generic as `str`.

Every provider is a singleton. There are no scopes — see Non-goals.

### Resources

A constructor declared as `AsyncIterator[T]` is a resource: the code before `yield`
runs at construction, the code after it runs at shutdown. Both a plain statement
after the `yield` and a `try/finally` work.

```python
async def new_pool(config: Config) -> AsyncIterator[Pool]:
    pool = await asyncpg.create_pool(config.dsn)
    try:
        yield pool
    finally:
        await pool.close()
```

Prefer this over `Hook` where you can: the resource and its cleanup stay in one
place. `Hook` is there for the cases where the thing to start is not the thing the
constructor builds.

## Built-in services

Ask for any of these in a constructor or an invokable and di_fx supplies it:

- **`Lifecycle`** — append startup and shutdown hooks.
- **`Shutdowner`** — `await shutdowner.shutdown("reason")` stops the application
  from anywhere inside it.
- **`DotGraph`** — the dependency graph, for rendering with Graphviz.

## Validation

The graph is validated when the application starts: every dependency has to be
satisfiable by a provider, a supplied value, a built-in or the base type behind a
`Named`, and there must be no cycles. Call `app.validate()` yourself for a
pre-flight check, or pass `App(..., validate=False)` to skip it.

```
ValidationError: Validation failed with 1 error(s):
  - Provider Worker depends on Database, but no provider is registered for Database
```

## Testing

```python
import pytest
from di_fx import App, Provide, Supply


@pytest.fixture
def app():
    return App(
        Supply(Config(dsn="postgresql://localhost/test")),
        Provide(new_fake_database, new_worker),
    )


async def test_worker_uses_the_configured_database(app):
    worker = await app.resolve(Worker)

    assert worker.database.dsn.endswith("/test")
```

`resolve()` builds only what the requested type needs, without starting the
lifecycle. To exercise startup and shutdown, `await app.start()` and
`await app.stop()`. To substitute a dependency, build the component with a
different provider — there is no override mechanism.

## Non-goals

These are settled, not pending:

- **No Rust core.** The measured cost of a PyO3 call is a low per-call overhead on
  top of a large constant one, which pays off in hot loops and not in a graph that
  is resolved once at startup.
- **No hot reloading.** Not a dependency container's job.
- **No request scopes** before 1.0, possibly ever. Scopes are what the rest of the
  ecosystem competes on, and dishka does it well.
- **No performance claims** without a benchmark in this repository. There is none
  yet, so there are none.
- **One event loop per application.** Resolution is not thread-safe.

## Development

```bash
git clone https://github.com/smirnoffmg/di_fx.git
cd di_fx
make install-dev     # uv sync --dev

make format          # ruff format
make lint            # ruff check + mypy
make test            # pytest
make all
```

The examples under `examples/` are run in CI; they are the only thing that
assembles a container end to end, so keep them working.

## Further reading

- [di_fx and Uber-Fx](docs/uber_fx_comparison.md) — what carried over, what changed,
  and what is deliberately missing
- [Best practices](docs/best_practices.md)
- [Troubleshooting](docs/troubleshooting_guide.md)

## Acknowledgments

The design is Uber-Fx's: constructor functions, a type-keyed graph, and a lifecycle
split into initialization and execution. The mistakes are this project's own.

## License

MIT — see [LICENSE](LICENSE).
