# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

- `docs/rust_integration_benefits.md`, and the README's performance table, Rust
  extra, `request_scope` and `EnableHotReload` sections — none of which existed.

## [0.1.0] - 2026-09

Initial version.
