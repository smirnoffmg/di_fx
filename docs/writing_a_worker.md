# Writing a worker

This is the case di_fx exists for: a long-running asyncio process with no web
framework above it. Nothing else owns the lifecycle, so the application has to build
its own graph, start its workers, and stop them again when the process is asked to
exit.

The complete, runnable version of everything below is
[`examples/queue_consumer.py`](../examples/queue_consumer.py), which CI runs.

## The shape

```python
app = App(
    Supply(Config()),                     # values you already have
    Provide(new_queue, new_consumer),     # how to build everything else
    Invoke(fill_the_queue),               # what to actually do at startup
)

asyncio.run(app.run())
```

`run()` starts the application, waits, and stops it when a `Shutdowner` asks or the
process gets SIGINT or SIGTERM.

## Connections are resources, not hooks

Anything you open and have to close is a provider declared as `AsyncIterator[T]`.
The code before the `yield` runs during initialization; the code after it runs at
shutdown, after everything that depends on it has already stopped.

```python
async def new_queue(config: Config) -> AsyncIterator[Queue]:
    queue = await connect(config.url)
    try:
        yield queue
    finally:
        await queue.close()
```

You do not have to remember to close it, and you do not have to say where in the
shutdown order it belongs: it goes in the reverse of the order it was built, which
is what you meant.

## Work that runs in the background is a hook

A consumer is not a resource — it is something that starts and stops. Ask for
`Lifecycle` in the constructor and append a `Hook`:

```python
def new_consumer(queue: Queue, lifecycle: Lifecycle) -> Consumer:
    consumer = Consumer(queue)
    lifecycle.append(
        Hook(on_start=consumer.start, on_stop=consumer.stop, name="consumer")
    )
    return consumer
```

`start` creates the task, `stop` cancels it and waits:

```python
async def start(self) -> None:
    self._task = asyncio.create_task(self._consume())

async def stop(self) -> None:
    self._task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await self._task
```

Both run under the hook's `timeout` (30 seconds by default). A `stop` that hangs is
reported as `HookTimeoutError` rather than hanging the process forever.

## Nothing happens without an Invoke

Constructors are lazy. `Provide(new_consumer)` on its own builds nothing, so the
consumer never exists and its hook is never appended. Something has to ask:

```python
async def fill_the_queue(queue: Queue, consumer: Consumer) -> None:
    ...
```

Invokables are the roots of the graph. If a worker seems not to start, this is
almost always why: nothing depends on it.

The same rule explains a mistake that is easy to make — resolving after startup:

```python
async with app:
    consumer = await app.resolve(Consumer)   # too late
```

By the time the block is entered the startup hooks have already run, so a
constructor appending one here raises. Put the work behind an `Invoke` instead.

## Stopping on purpose

Ask for `Shutdowner` anywhere and call it:

```python
async def _consume(self) -> None:
    while True:
        message = await self._queue.get()
        if message is POISON:
            await self._shutdowner.shutdown("poison pill")
```

This is the same path SIGTERM takes, so the shutdown sequence is identical whether
the process decided to stop or something outside it did.

## Failure

- A constructor that raises during initialization stops the startup, and everything
  already built is released — resources included, even though the lifecycle had not
  started yet.
- A startup hook that raises rolls back only the hooks that actually started, in
  reverse, and then the error is raised.
- A shutdown step that fails does not stop the others. All the failures are raised
  together as an `ExceptionGroup`, so nothing is silently skipped.

## Checking the graph before you deploy it

`App(...)` validates on `start()`. To fail earlier — in a test, or in a `--check`
flag on your CLI — call it yourself:

```python
def test_the_application_graph_is_complete():
    build_app().validate()
```

The error names the missing type and everything that wanted it:

```
No provider registered for type Config
  required by Database (new_database in module "storage")
  required by Worker (new_worker)
  required by invokable run
```
