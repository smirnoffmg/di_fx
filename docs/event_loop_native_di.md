# Event Loop Native DI Architecture

## Core Philosophy: Event Loop as Foundation

Instead of building our own scheduling and concurrency layer, we make **Python's event loop the heart** of our DI system. Every operation becomes an event loop citizen.

## Architecture Overview

```python
import asyncio
from typing import Dict, Set, Any, Optional, Callable, Awaitable
from contextvars import ContextVar
from weakref import WeakSet

class EventLoopNativeDI:
    """DI container that is deeply integrated with asyncio event loop"""
    
    def __init__(self):
        # Event loop integration
        self.loop = None  # Set when first used
        self._resolution_tasks: Dict[type, asyncio.Task] = {}
        self._lifecycle_tasks: Set[asyncio.Task] = WeakSet()
        
        # Context variables for request scoping
        self._request_context: ContextVar[dict] = ContextVar('request_context', default={})
        
        # Event-driven lifecycle management
        self._startup_callbacks: List[Callable[[], Awaitable[None]]] = []
        self._shutdown_callbacks: List[Callable[[], Awaitable[None]]] = []
        
        # Event loop scheduling
        self._startup_event = asyncio.Event()
        self._shutdown_event = asyncio.Event()
```

## 1. Event Loop Native Service Resolution

### Traditional Approach vs Event Loop Native

**Traditional (Blocking)**:
```python
# Traditional - blocks until resolution complete
def resolve(self, service_type: Type[T]) -> T:
    # Synchronous resolution
    instance = self._create_instance(service_type)
    return instance
```

**Event Loop Native**:
```python
class EventLoopDI:
    async def resolve(self, service_type: Type[T]) -> T:
        """Resolve service using event loop scheduling"""
        
        # Ensure we're in event loop context
        loop = self._get_event_loop()
        
        # Check if already being resolved (avoid duplicates)
        if service_type in self._resolution_tasks:
            return await self._resolution_tasks[service_type]
        
        # Schedule resolution as event loop task
        task = loop.create_task(self._resolve_service(service_type))
        self._resolution_tasks[service_type] = task
        
        try:
            instance = await task
            return instance
        finally:
            # Clean up task reference
            self._resolution_tasks.pop(service_type, None)
    
    async def _resolve_service(self, service_type: Type[T]) -> T:
        """Internal resolution using event loop cooperation"""
        
        # Yield control to event loop frequently
        await asyncio.sleep(0)
        
        # Get constructor function
        constructor = self._get_constructor(service_type)
        
        # Resolve dependencies concurrently
        dependencies = await self._resolve_dependencies_concurrent(constructor)
        
        # Yield control before instantiation
        await asyncio.sleep(0)
        
        # Create instance
        if asyncio.iscoroutinefunction(constructor):
            instance = await constructor(**dependencies)
        else:
            # Run sync constructor in thread pool to avoid blocking
            instance = await loop.run_in_executor(None, constructor, **dependencies)
        
        return instance
```

### Concurrent Dependency Resolution

```python
async def _resolve_dependencies_concurrent(self, constructor: Callable) -> Dict[str, Any]:
    """Resolve all dependencies concurrently using event loop"""
    
    dependency_types = self._analyze_dependencies(constructor)
    
    # Create concurrent resolution tasks
    resolution_tasks = {
        param_name: self.resolve(param_type)
        for param_name, param_type in dependency_types.items()
    }
    
    # Wait for all dependencies concurrently
    dependencies = {}
    for param_name, task in resolution_tasks.items():
        dependencies[param_name] = await task
    
    return dependencies
```

## 2. Event Loop Native Lifecycle Management

### Lifecycle Hooks as Event Loop Tasks

```python
class LifecycleManager:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self._startup_hooks: List[Hook] = []
        self._shutdown_hooks: List[Hook] = []
        self._running_tasks: Set[asyncio.Task] = set()
    
    async def start_all_services(self) -> None:
        """Start all services using event loop task scheduling"""
        
        # Group hooks by dependency level for concurrent execution
        dependency_levels = self._group_by_dependency_level()
        
        for level_hooks in dependency_levels:
            # Start all hooks at this level concurrently
            tasks = []
            for hook in level_hooks:
                task = self.loop.create_task(self._execute_hook_safe(hook))
                tasks.append(task)
                self._running_tasks.add(task)
            
            # Wait for this level to complete before moving to next
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Clean up completed tasks
            self._running_tasks -= set(tasks)
    
    async def _execute_hook_safe(self, hook: Hook) -> None:
        """Execute lifecycle hook with event loop integration"""
        try:
            # Set up cancellation support
            async with asyncio.timeout(hook.timeout):
                if hook.on_start:
                    await hook.on_start()
                    
        except asyncio.TimeoutError:
            logger.error(f"Hook {hook.name} timed out after {hook.timeout}s")
            raise
        except asyncio.CancelledError:
            logger.info(f"Hook {hook.name} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Hook {hook.name} failed: {e}")
            raise
```

### Background Services as Event Loop Tasks

```python
def new_background_worker(
    lifecycle: EventLoopLifecycle,
    config: WorkerConfig,
) -> BackgroundWorker:
    """Background worker that integrates with event loop"""
    
    worker = BackgroundWorker(config)
    
    async def start_worker():
        # Schedule worker as event loop task
        task = asyncio.create_task(worker.run_forever())
        
        # Register task for graceful shutdown
        lifecycle.register_background_task(task)
        
        # Monitor task health
        lifecycle.monitor_task(task, restart_on_failure=True)
    
    async def stop_worker():
        # Graceful cancellation through event loop
        await lifecycle.cancel_background_tasks()
    
    lifecycle.on_start(start_worker)
    lifecycle.on_stop(stop_worker)
    
    return worker

class BackgroundWorker:
    async def run_forever(self):
        """Event loop native background processing"""
        try:
            while True:
                # Process work cooperatively
                await self.process_batch()
                
                # Yield control to event loop
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.info("Background worker cancelled gracefully")
            raise
```

## 3. Request Scoping with Context Variables

```python
from contextvars import ContextVar, copy_context
from typing import Optional

# Request-scoped context
request_scope: ContextVar[Dict[str, Any]] = ContextVar('request_scope', default={})

class RequestScopedContainer:
    """Container that provides request-scoped dependencies"""
    
    async def resolve_scoped(self, service_type: Type[T], scope: str = "request") -> T:
        """Resolve service with proper scoping using context variables"""
        
        if scope == "request":
            # Check request-scoped cache
            ctx = request_scope.get({})
            cache_key = f"{service_type.__name__}:{id(asyncio.current_task())}"
            
            if cache_key in ctx:
                return ctx[cache_key]
            
            # Create new instance for this request
            instance = await self.resolve(service_type)
            
            # Cache in request context
            ctx = ctx.copy()
            ctx[cache_key] = instance
            request_scope.set(ctx)
            
            return instance
        
        # Fallback to singleton scope
        return await self.resolve(service_type)

# Web framework integration
async def handle_request(request, handler):
    """Web request handler with automatic scoping"""
    
    # Create new context for this request
    ctx = copy_context()
    
    # Run handler in isolated context
    return await ctx.run(handler, request)
```

## 4. Event-Driven Hot Reloading

```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class EventLoopHotReloader:
    """Hot reloader integrated with event loop"""
    
    def __init__(self, container: EventLoopDI):
        self.container = container
        self.reload_queue = asyncio.Queue()
        self.observer = Observer()
    
    async def start_watching(self, paths: List[str]):
        """Start file watching using event loop"""
        
        # Set up file system watcher
        handler = AsyncFileHandler(self.reload_queue)
        for path in paths:
            self.observer.schedule(handler, path, recursive=True)
        
        self.observer.start()
        
        # Start reload processor as event loop task
        asyncio.create_task(self._process_reload_events())
    
    async def _process_reload_events(self):
        """Process reload events in event loop"""
        while True:
            try:
                # Wait for reload event
                event = await self.reload_queue.get()
                
                # Schedule reload as event loop task
                asyncio.create_task(self._reload_service(event.service_type))
                
                # Mark task as done
                self.reload_queue.task_done()
                
            except asyncio.CancelledError:
                break
    
    async def _reload_service(self, service_type: Type):
        """Reload service with zero downtime using event loop"""
        
        # Create new instance in background
        new_instance = await self.container.resolve_fresh(service_type)
        
        # Atomic swap using event loop scheduling
        await self.container.replace_instance(service_type, new_instance)
        
        logger.info(f"Hot reloaded {service_type.__name__}")

class AsyncFileHandler(FileSystemEventHandler):
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self.loop = asyncio.get_event_loop()
    
    def on_modified(self, event):
        # Schedule queue put in event loop
        asyncio.run_coroutine_threadsafe(
            self.queue.put(ReloadEvent(event.src_path)),
            self.loop
        )
```

## 5. Event Loop Native App Container

```python
class EventLoopApp:
    """Main application container built on event loop foundations"""
    
    def __init__(self, *components):
        self.container = EventLoopDI()
        self.lifecycle = EventLoopLifecycle()
        self._shutdown_event = asyncio.Event()
        self._startup_complete = asyncio.Event()
        
        self._register_components(components)
    
    async def run(self):
        """Run application using event loop as orchestrator"""
        
        # Get current event loop
        loop = asyncio.get_running_loop()
        
        # Set up signal handlers using event loop
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._signal_shutdown)
        
        try:
            # Start all services
            await self._startup_sequence()
            
            # Signal that startup is complete
            self._startup_complete.set()
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        finally:
            # Graceful shutdown
            await self._shutdown_sequence()
    
    async def _startup_sequence(self):
        """Event loop orchestrated startup"""
        
        # Phase 1: Validate dependency graph
        await self._validate_dependencies()
        
        # Phase 2: Initialize core services concurrently
        core_tasks = [
            asyncio.create_task(self._initialize_logging()),
            asyncio.create_task(self._initialize_config()),
            asyncio.create_task(self._initialize_metrics()),
        ]
        await asyncio.gather(*core_tasks)
        
        # Phase 3: Start application services
        await self.lifecycle.start_all_services()
        
        # Phase 4: Run startup hooks
        await self._run_startup_hooks()
    
    async def _shutdown_sequence(self):
        """Event loop orchestrated shutdown"""
        
        # Phase 1: Stop accepting new work
        await self._stop_accepting_requests()
        
        # Phase 2: Finish in-flight requests (with timeout)
        try:
            async with asyncio.timeout(30):
                await self._wait_for_inflight_requests()
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout - forcing termination")
        
        # Phase 3: Stop services in reverse order
        await self.lifecycle.stop_all_services()
        
        # Phase 4: Final cleanup
        await self._final_cleanup()
    
    def _signal_shutdown(self):
        """Signal handler that schedules shutdown in event loop"""
        logger.info("Received shutdown signal")
        asyncio.create_task(self._graceful_shutdown())
    
    async def _graceful_shutdown(self):
        """Graceful shutdown orchestrated by event loop"""
        self._shutdown_event.set()
```

## 6. Rust Integration with Event Loop

Even with Rust performance optimizations, we maintain event loop integration:

```python
# Python side - still event loop native
class HybridEventLoopDI(EventLoopDI):
    def __init__(self):
        super().__init__()
        # Initialize Rust core with event loop integration
        self._rust_core = di_fx_core.DependencyResolver()
    
    async def resolve(self, service_type: Type[T]) -> T:
        """Resolve using Rust core but staying event loop native"""
        
        # Yield to event loop before Rust operation
        await asyncio.sleep(0)
        
        # Call Rust resolver (PyO3-asyncio makes this awaitable)
        instance = await self._rust_core.resolve_async(service_type)
        
        # Yield to event loop after Rust operation
        await asyncio.sleep(0)
        
        return instance
```

```rust
// Rust side - PyO3-asyncio integration
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;

#[pymethods]
impl DependencyResolver {
    // Make Rust operations awaitable from Python
    fn resolve_async<'p>(&self, py: Python<'p>, service_type: &str) -> PyResult<&'p PyAny> {
        let service_type = service_type.to_owned();
        let resolver = self.clone();
        
        future_into_py(py, async move {
            // Rust async operation
            let result = resolver.resolve_internal(&service_type).await?;
            
            // Yield back to Python event loop
            tokio::task::yield_now().await;
            
            Ok(result)
        })
    }
}
```

## Benefits of Event Loop Native Architecture

### 1. **True Async Integration**
```python
# Everything is naturally async and composable
async def handle_request(request):
    async with app.request_scope():
        user_service = await app.resolve(UserService)
        cache = await app.resolve(CacheService)
        
        # All operations are event loop native
        user = await user_service.get_user(request.user_id)
        await cache.set(f"user:{user.id}", user)
        
        return user.to_dict()
```

### 2. **Perfect Cancellation Support**
```python
# Automatic cancellation propagation through DI
async def cancellable_operation():
    try:
        service = await app.resolve(SlowService)
        result = await service.slow_operation()
        return result
    except asyncio.CancelledError:
        # Cancellation propagates through entire DI chain
        logger.info("Operation cancelled gracefully")
        raise
```

### 3. **Native Debugging and Monitoring**
```python
# Standard asyncio debugging tools work perfectly
import asyncio

# Enable asyncio debug mode
asyncio.get_event_loop().set_debug(True)

# All DI operations show up in asyncio task monitoring
tasks = asyncio.all_tasks()
for task in tasks:
    print(f"Task: {task.get_name()}, State: {task._state}")
```

### 4. **Resource Efficiency**
- **No additional threads** - everything uses the event loop
- **Cooperative concurrency** - better resource utilization
- **Natural backpressure** - event loop handles overload gracefully
- **Memory efficiency** - single event loop, no thread overhead

## Usage Example

```python
# Clean, event loop native API
async def main():
    app = EventLoopApp(
        Provide(
            new_database_service,
            new_cache_service,
            new_user_service,
            new_http_server,
        ),
        Supply(
            DatabaseConfig.from_env(),
            CacheConfig.from_env(),
        ),
    )
    
    # Run everything on the event loop
    await app.run()

# Single event loop handles everything:
# - Dependency resolution
# - Service lifecycle
# - Background tasks  
# - Request handling
# - Hot reloading
# - Graceful shutdown

if __name__ == "__main__":
    asyncio.run(main())
```

This event loop native architecture makes di_fx a **true citizen of Python's async ecosystem** while maintaining all the performance benefits of Rust integration!