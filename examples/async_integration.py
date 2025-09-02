"""
Advanced asyncio integration example for di_fx.

This example demonstrates the framework's integration with asyncio
event loop, background tasks, and proper lifecycle management.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

from di_fx import Component, Hook, Lifecycle, Provide, Supply


@dataclass
class Config:
    """Application configuration."""

    name: str
    worker_count: int = 3


class BackgroundWorker:
    """Background worker that runs as an asyncio task."""

    def __init__(self, config: Config, worker_id: int):
        self.config = config
        self.worker_id = worker_id
        self.running = False
        self.task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        """Start the background worker."""
        self.running = True
        print(f"Starting worker {self.worker_id} for {self.config.name}")

    async def stop(self) -> None:
        """Stop the background worker."""
        self.running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        print(f"Stopped worker {self.worker_id}")

    async def run_forever(self) -> None:
        """Main worker loop."""
        while self.running:
            print(f"Worker {self.worker_id} processing...")
            await asyncio.sleep(1)


class WorkerManager:
    """Manages multiple background workers."""

    def __init__(self, config: Config, lifecycle: Lifecycle):
        self.config = config
        self.workers: list[BackgroundWorker] = []

        # Create workers
        for i in range(config.worker_count):
            worker = BackgroundWorker(config, i)
            self.workers.append(worker)

            # Register lifecycle hooks for each worker
            lifecycle.append(
                Hook(on_start=worker.start, on_stop=worker.stop, name=f"worker_{i}")
            )

    async def start_workers(self, app: Component) -> None:
        """Start all background workers as asyncio tasks."""
        for worker in self.workers:
            # Create and track the worker task
            worker.task = app.create_task(worker.run_forever())

    async def stop_workers(self) -> None:
        """Stop all background workers."""
        for worker in self.workers:
            await worker.stop()


async def new_worker_manager(config: Config, lifecycle: Lifecycle) -> WorkerManager:
    """Create worker manager."""
    return WorkerManager(config, lifecycle)


async def main() -> None:
    """Main application function demonstrating asyncio integration."""
    # Create the application
    app = Component(
        Provide(new_worker_manager),
        Supply(Config(name="AsyncApp", worker_count=2)),
    )

    # Use the application lifecycle
    async with app.lifecycle():
        print("Application started!")

        # Resolve dependencies (this registers the lifecycle hooks)
        await app.resolve(WorkerManager)

        print("Background workers registered. Running for 3 seconds...")
        await asyncio.sleep(3)

        print("Stopping application...")

    print("Application stopped!")


if __name__ == "__main__":
    asyncio.run(main())
