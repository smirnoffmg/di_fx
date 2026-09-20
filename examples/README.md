# Examples

Every file here runs on its own and terminates, and CI runs all of them on every
push — so if one is wrong, the build says so.

```bash
uv run python examples/01_minimal.py
```

Read them in order. The first three are the case di_fx is for: a long-running
asyncio process with no web framework above it.

| | Shows |
|---|---|
| [`01_minimal.py`](01_minimal.py) | The smallest complete application: `Supply`, `Provide`, a resource declared as `AsyncIterator`, a lifecycle `Hook`, and `Invoke` as the root of the graph. |
| [`02_queue_consumer.py`](02_queue_consumer.py) | A worker process end to end — connect, consume, stop on `Shutdowner` or SIGTERM. The guide for it is [docs/writing_a_worker.md](../docs/writing_a_worker.md). |
| [`03_background_tasks.py`](03_background_tasks.py) | Several workers under one lifecycle: a hook each, asyncio tasks started and cancelled, everything unwinding in reverse. |
| [`04_modules.py`](04_modules.py) | Splitting an application into named `Component` modules, and `Annotated` aliases so two providers returning `str` do not collide. |
| [`05_named.py`](05_named.py) | `Named` for two of the same thing — a primary and a replica database. |
| [`06_builtin_services.py`](06_builtin_services.py) | `Shutdowner` and `DotGraph`, which di_fx supplies without being asked. |
| [`07_validation.py`](07_validation.py) | `validate()` as a pre-flight check, and what a missing dependency looks like. |

## Two things these examples are careful about

**Nothing is built unless an `Invoke` asks for it.** Constructors are lazy, so a
provider nothing depends on never runs and never appends its hook. If a worker
seems not to start, that is almost always why.

**Resolving after startup is too late to register a hook.** By the time
`async with app:` has been entered, the startup hooks have already run. Work that
needs a constructor to append one belongs behind an `Invoke`, which is what these
examples do.
