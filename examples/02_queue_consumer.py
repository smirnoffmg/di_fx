"""A queue consumer: the shape di_fx is for.

No web framework, so nothing else owns the process lifecycle: the application has
to build its own graph, start its workers, and stop them again when the process is
asked to exit.

Run it and it consumes ten messages, then shuts itself down. Send it SIGTERM and it
stops mid-flight, draining in the reverse of the order things were built.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from di_fx import App, Hook, Invoke, Lifecycle, Provide, Shutdowner, Supply

logger = logging.getLogger("consumer")


@dataclass
class Config:
    queue_name: str = "jobs"
    messages_to_process: int = 10


class Queue:
    """Stands in for a real broker connection."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._messages = asyncio.Queue[str]()

    async def publish(self, message: str) -> None:
        await self._messages.put(message)

    async def get(self) -> str:
        return await self._messages.get()


class Consumer:
    def __init__(self, queue: Queue, shutdowner: Shutdowner, budget: int) -> None:
        self._queue = queue
        self._shutdowner = shutdowner
        self._budget = budget
        self._task: asyncio.Task[None] | None = None
        self.processed = 0

    async def start(self) -> None:
        self._task = asyncio.create_task(self._consume())
        logger.info("consumer started on %s", self._queue.name)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("consumer stopped after %d message(s)", self.processed)

    async def _consume(self) -> None:
        while True:
            message = await self._queue.get()
            self.processed += 1
            logger.info("handled %s", message)
            if self.processed >= self._budget:
                await self._shutdowner.shutdown("budget exhausted")


# A resource: the code before the yield is startup, the code after it is shutdown.
async def new_queue(config: Config) -> AsyncIterator[Queue]:
    queue = Queue(config.queue_name)
    logger.info("connected to %s", queue.name)
    try:
        yield queue
    finally:
        logger.info("disconnected from %s", queue.name)


# A constructor that needs to start something asks for Lifecycle and appends a hook.
def new_consumer(
    queue: Queue, shutdowner: Shutdowner, lifecycle: Lifecycle, config: Config
) -> Consumer:
    consumer = Consumer(queue, shutdowner, config.messages_to_process)
    lifecycle.append(
        Hook(on_start=consumer.start, on_stop=consumer.stop, name="consumer")
    )
    return consumer


# Invoke is what pulls the graph into existence. Without it nothing is constructed,
# and a constructor that never runs never registers its hooks.
async def fill_the_queue(
    queue: Queue,
    config: Config,
    consumer: Consumer,  # noqa: ARG001 - asked for so that it gets built
) -> None:
    """Publish the work, and bring the consumer into existence while doing it.

    The consumer parameter is never touched here. That is the point: nothing else
    depends on the Consumer, so without this line it would never be constructed and
    its lifecycle hook would never be appended. In a provider an unused parameter is
    a mistake; in an invokable it is how you root part of the graph.
    """
    for number in range(config.messages_to_process):
        await queue.publish(f"job-{number}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    app = App(
        Supply(Config()),
        Provide(new_queue, new_consumer),
        Invoke(fill_the_queue),
    )

    asyncio.run(app.run())


if __name__ == "__main__":
    main()
