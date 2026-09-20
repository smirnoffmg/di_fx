# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-09-20

### Added

- **Errors say who needed the missing thing.** A failed resolution reports the chain
  back to the invokable that started it, naming each constructor and the module it
  was declared in:

  ```
  No provider registered for type Config
    required by Database (new_database in module "storage")
    required by Worker (new_worker)
    required by invokable run
  ```

  Validation errors name the constructor and module too. This is what the name on a
  `Component` is for; until now it was accepted and never used.
- **`examples/queue_consumer.py`** and [docs/writing_a_worker.md](docs/writing_a_worker.md):
  the case di_fx is for, end to end — resources, background work, invokables as the
  roots of the graph, programmatic shutdown, and what happens when each of them fails.
- Debug logging for the initialization and execution phases, and for each hook as it
  starts and stops. Nothing is logged above DEBUG except that the application started
  and is stopping.
- `Lifecycle.entry_count()`: hooks and resources together, where `len()` counts hooks.

### Fixed

- Nothing. `DotGraph` turned out to work; it was simply untested, and now has tests.
  Coverage 95% -> 97.5%.

## [0.3.0] - 2026-09-20

Structural release. The public API changes; behaviour does not, except where noted.

### Changed

- **`App` is the runnable application; `Component` is inert.** `Provide`, `Supply`,
  `Invoke` and `Component` are plain records now — they describe an application and
  know nothing about running one. `Component(...).start()` becomes
  `App(Component(...)).start()`, or just `App(Provide(...), Supply(...))`.

  They used to inherit `Component`, which was itself the application container. That
  gave `get_providers()` two different meanings depending on the receiver (Provide
  components vs Provider records), which is what broke nesting; it built a full
  orchestrator with nine managers inside every `Provide(...)`, five of them for an
  application of three components; and it left the provider dictionary living in
  three copies with no owner.

- **`async with app:` starts on entry and stops on exit.** `Component.lifecycle()`
  called `start()` on the way *out* of the block, so everything inside ran before any
  startup hook. It survives as a deprecated alias for `async with`.

  Consequence: resolving a type whose constructor appends a lifecycle hook has to
  happen during initialization, which means from an `Invoke` function. Two examples
  were doing it from inside the context block and have been restructured.

- **One graph.** `flatten()` walks the registrations into an immutable `Graph` that
  owns the providers, values and invokables; `Resolver` and the validator read the
  same structure through the same `can_resolve()` predicate.

- **Exceptions live in `di_fx.errors`** under a `DiFxError` base, with
  `MissingProviderError`, `DuplicateProviderError` and `CircularDependencyError` as
  `ValidationError` subclasses, so existing `except ValidationError` still catches
  them. `HookTimeoutError` moved there from `di_fx.lifecycle`.

- **`__all__` is 19 names.** The internal managers are no longer exported.

### Removed

- `AppOrchestrator`, `BuiltinServiceManager`, `ComponentProcessor`,
  `ComponentProcessorManager`, `DependencyResolver`, `ErrorHandler`,
  `InvokableExecutor`, `LifecycleManager`, `StateManager`, `ValidationManager` — 15
  modules, replaced by `app.py`, `graph.py`, `registrations.py`, `resolver.py` and
  `errors.py`. 21 modules become 11, and 1087 statements become 612.
- `Provider.singleton`, which was never `False`. Every provider is a singleton;
  scopes are a stated non-goal.
- `ErrorHandler.safe_execute` and the retry/backoff layer: no callers.

## [0.2.0] - 2026-09-20

### Scope

di_fx is now aimed at asyncio applications that have no web framework above them:
workers, queue consumers, daemons. Web applications are pointed at dishka plus the
framework's own `lifespan`. A Rust core, hot reloading, request scopes and
performance claims are non-goals — see the README.

### Fixed

- **Lifecycle hooks can be registered from a provider again.** `start()` began the
  lifecycle before running the invokables, but dependency resolution happens inside
  the invokables, so every constructor ran after the lifecycle had latched and
  `Lifecycle.append()` rejected it. The documented pattern was impossible to express.
- **`validate()` no longer rejects valid graphs.** It was built from the providers
  alone, so any graph using `Supply` or a built-in service failed validation.
  Providers, supplied values, built-ins and the base type behind a `Named` now go
  through one predicate shared with the resolver. Invokable dependencies are
  validated too.
- **`Shutdowner` injected into a constructor works.** The resolver built its own
  `Shutdowner` with a no-op callback while the application wired up a different one.
- **Shutdown no longer crashes when tasks are tracked.** `LifecycleManager.stop()`
  iterated the task set while awaiting cancellation, and the done callbacks mutated
  it: `RuntimeError: Set changed size during iteration` on every shutdown that had
  created a task. The error was then swallowed, skipping the remaining cleanup.
- **`Hook.timeout` is enforced.** It had been declared with a 30s default and never
  used.
- **A failed startup rolls back only what started**, in reverse order, instead of
  running every `on_stop`.
- **Shutdown failures are reported.** Every step still runs; the failures are raised
  together as an `ExceptionGroup` instead of being logged and dropped.
- **Components nest to any depth.** `Component(Component(Component(...)))` raised
  `AttributeError: 'Provide' object has no attribute 'return_type'` at the third
  level.
- **Cycles are reported with their path** and only once, by the validator and by the
  resolver — which previously had no cycle guard at all and ran to the recursion limit.
- **Resource cleanup after `yield` runs.** Generator providers are resumed instead of
  closed, so a plain statement after the `yield` works, not only `try/finally`.
- Four of the six shipped examples did not run. They do now, and CI runs them.

### Changed

- **Two providers for the same type is an error** (`DuplicateProviderError`) instead
  of a silent last-wins. Uber-Fx answers "several implementations of one interface"
  with value groups, which di_fx does not have.
- **Only `AsyncIterator` and friends are unwrapped to their inner type.** Unwrapping
  every generic meant `Annotated[str, "server"]` also claimed plain `str`.
- **`run()` waits on an event** instead of polling every 100ms, and installs SIGINT
  and SIGTERM handlers for its duration, removing them afterwards.
- **The graph is validated automatically at `start()`**; pass
  `Component(..., validate=False)` to skip it.
- **`Component` takes a name again** as a leading string, the way `fx.Module("server",
  ...)` reads. It had been removed along with `Module`.
- **`stop()` without a preceding `start()` runs no hooks.** Only what started is
  stopped.
- Missing providers raise `ValidationError`, not `KeyError`.
- The library logs instead of printing. No `print()` remains in `src/`.
- No runtime dependencies: `typing-extensions` was declared but never imported.

### Removed

- `docs/rust_integration_benefits.md`, `docs/framework_integrations.md` and
  `docs/event_loop_native_di.md`: the Rust core and the web integrations are
  non-goals now. `docs/uber_fx_comparison.md` is rewritten against the current API.
- The README's performance table, Rust extra, `request_scope` and `EnableHotReload`
  sections — none of which existed.
- `typing-extensions` (never imported) and `pytest-benchmark` (nothing to benchmark).

## [0.1.0] - 2026-09

Initial version.
