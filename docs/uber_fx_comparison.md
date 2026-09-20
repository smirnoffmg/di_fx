# di_fx and Uber-Fx

di_fx takes its model from [Uber-Fx](https://github.com/uber-go/fx): constructor
functions instead of classes, a graph keyed by type, and an application split into
an initialization phase and an execution phase. This page records what carried over,
what changed on purpose, and what is not there.

## What maps directly

| Uber-Fx | di_fx |
|---|---|
| `fx.Provide(NewService)` | `Provide(new_service)` |
| `fx.Supply(value)` | `Supply(value)` |
| `fx.Invoke(setupRoutes)` | `Invoke(setup_routes)` |
| `fx.Module("server", ...)` | `Component("server", ...)` |
| `fx.Lifecycle` / `fx.Hook{OnStart, OnStop}` | `Lifecycle` / `Hook(on_start=..., on_stop=...)` |
| `fx.Shutdowner` | `Shutdowner` |
| `fx.DotGraph` | `DotGraph` |
| `fx.Annotate(New, fx.As(new(Iface)))` | `Annotate(new_thing, As(Iface))` |
| `fx.Named` | `Named("primary", Database)` |
| `app.Run()` | `await app.run()` |

The two phases are the same, and for the same reason. During initialization Fx runs
the functions passed to `fx.Invoke`, calling constructors as needed; the hooks those
constructors appended run afterwards, during execution. di_fx does exactly this, and
getting the order backwards was the framework's most serious bug until 0.2.

## Where di_fx diverges on purpose

**Resources are generators, not hooks.** Go has no generators and no context
managers, so in Fx every startup and shutdown pair is a `Hook`. In Python the
natural spelling is a provider that yields:

```python
async def new_pool(config: Config) -> AsyncIterator[Pool]:
    pool = await asyncpg.create_pool(config.dsn)
    try:
        yield pool
    finally:
        await pool.close()
```

`Hook` still exists, for the case where the thing to start is not the thing the
constructor builds, and both land in one ordered list that unwinds together. But the
generator is the documented idiom here, where in Fx it could not exist at all.

**Types are Python types.** Fx distinguishes `*sql.DB` from `*Wrapper` for free; in
Python a lot of things are `str`. Where Fx would rely on distinct struct types,
di_fx users reach for `Named`, `Annotated[str, "dsn"]` or a small class. Two
providers returning the same type is an error, as it is in Fx.

**Async everywhere.** Constructors may be `async def`, resolution is a coroutine,
and hooks are awaited with a timeout.

## What Fx has and di_fx does not

- **Value groups** (`fx.Out` / `group:"routes"`). This is Fx's answer to "several
  implementations of one interface". di_fx has no equivalent, so registering two
  providers for one interface is refused rather than silently resolved.
- **Decorators** (`fx.Decorate`) for wrapping an already-provided type.
- **Parameter and result objects** (`fx.In` / `fx.Out` structs). Python's keyword
  arguments and dataclasses cover most of what they are for.
- **`fx.Replace` and `fx.Decorate` for tests.** To substitute a dependency, build the
  component with a different provider.
- **The logging integration** (`fx.WithLogger`, the event stream). di_fx logs through
  the standard library and reports far less.

## What neither has

Scopes. Fx is a process-lifetime container and so is di_fx; per-request objects are
not part of the model. In Python that gap is filled by
[dishka](https://github.com/reagento/dishka), which is the right tool for a web
application — see the README's scope section.
