# Troubleshooting Guide

## Common Issues and Solutions

### Dependency Resolution Errors

#### Error: `DependencyError: Cannot resolve SomeService: No provider found`

**Symptoms:**
```python
DependencyError: Cannot resolve UserService: No provider found
```

**Causes and Solutions:**

1. **Missing Provider Registration**
   ```python
   # Problem: Service not registered
   app = App(
       # new_user_service is missing from Provide()
       Provide(new_database_service)
   )
   
   # Solution: Add the missing provider
   app = App(
       Provide(
           new_database_service,
           new_user_service,  # Add this
       )
   )
   ```

2. **Incorrect Type Annotation**
   ```python
   # Problem: Type mismatch
   def new_user_service(db: Database) -> UserService:  # Expects Database
       return UserService(db)
   
   def new_database_service() -> DatabaseService:  # Provides DatabaseService
       return DatabaseService()
   
   # Solution: Fix type annotations
   def new_user_service(db: DatabaseService) -> UserService:  # Now matches
       return UserService(db)
   ```

3. **Missing Configuration**
   ```python
   # Problem: Configuration not supplied
   def new_database_service(config: DatabaseConfig) -> DatabaseService:
       return DatabaseService(config)
   
   app = App(
       Provide(new_database_service)
       # Missing Supply(DatabaseConfig(...))
   )
   
   # Solution: Supply the configuration
   app = App(
       Provide(new_database_service),
       Supply(DatabaseConfig.from_env()),  # Add this
   )
   ```

#### Error: `CircularDependencyError`

**Symptoms:**
```python
CircularDependencyError: Circular dependency detected: UserService -> OrderService -> UserService
```

**Causes and Solutions:**

1. **Direct Circular Dependency**
   ```python
   # Problem: A depends on B, B depends on A
   def new_user_service(order_service: OrderService) -> UserService:
       return UserService(order_service)
   
   def new_order_service(user_service: UserService) -> OrderService:
       return OrderService(user_service)
   
   # Solution 1: Extract shared logic
   def new_user_repository(db: DatabaseService) -> UserRepository:
       return UserRepository(db)
   
   def new_order_repository(db: DatabaseService) -> OrderRepository:
       return OrderRepository(db)
   
   def new_user_service(user_repo: UserRepository) -> UserService:
       return UserService(user_repo)
   
   def new_order_service(order_repo: OrderRepository) -> OrderService:
       return OrderService(order_repo)
   
   # Solution 2: Use event-driven architecture
   def new_user_service(event_bus: EventBus) -> UserService:
       return UserService(event_bus)
   
   def new_order_service(event_bus: EventBus) -> OrderService:
       service = OrderService(event_bus)
       event_bus.subscribe(UserCreated, service.handle_user_created)
       return service
   ```

### Lifecycle Issues

#### Error: `LifecycleError: Lifecycle start failed`

**Symptoms:**
```python
LifecycleError: Lifecycle start failed for DatabaseService: connection refused
```

**Debug Steps:**

1. **Check Service Status**
   ```bash
   # Verify external services are running
   pg_isready -h localhost -p 5432  # PostgreSQL
   redis-cli ping                   # Redis
   curl -f http://localhost:8080/health  # HTTP service
   ```

2. **Add Connection Testing**
   ```python
   def new_database_service(lifecycle: Lifecycle, config: DatabaseConfig) -> DatabaseService:
       service = DatabaseService(config)
       
       async def start_with_validation():
           try:
               await service.connect()
               # Test the connection
               await service.execute("SELECT 1")
               logger.info("Database connected successfully")
           except Exception as e:
               logger.error(f"Database connection failed: {e}")
               logger.error(f"Config: host={config.host}, port={config.port}")
               raise
       
       lifecycle.append(Hook(on_start=start_with_validation))
       return service
   ```

3. **Add Retry Logic**
   ```python
   async def start_with_retry():
       max_attempts = 3
       for attempt in range(max_attempts):
           try:
               await service.connect()
               break
           except Exception as e:
               if attempt == max_attempts - 1:
                   raise
               wait_time = 2 ** attempt
               logger.warning(f"Connection failed, retrying in {wait_time}s: {e}")
               await asyncio.sleep(wait_time)
   ```

#### Error: Application Hangs During Startup

**Symptoms:**
- Application starts but never completes initialization
- No error messages, just hangs indefinitely

**Debug Steps:**

1. **Add Timeout Debugging**
   ```python
   import asyncio
   import signal
   
   async def debug_startup():
       app = create_app()
       
       # Add timeout to detect hanging
       try:
           await asyncio.wait_for(app.start(), timeout=60.0)
       except asyncio.TimeoutError:
           logger.error("Startup timed out - likely deadlock or hanging operation")
           # Print stack traces of all tasks
           for task in asyncio.all_tasks():
               logger.error(f"Task: {task}")
               logger.error(task.get_stack())
           raise
   ```

2. **Add Progress Logging**
   ```python
   def new_slow_service(lifecycle: Lifecycle) -> SlowService:
       service = SlowService()
       
       async def start_with_logging():
           logger.info("Starting SlowService...")
           await service.initialize_phase_1()
           logger.info("SlowService phase 1 complete")
           await service.initialize_phase_2()
           logger.info("SlowService phase 2 complete")
           logger.info("SlowService fully started")
       
       lifecycle.append(Hook(on_start=start_with_logging))
       return service
   ```

3. **Check for Blocking Operations**
   ```python
   # Problem: Blocking operation in async context
   def new_bad_service(lifecycle: Lifecycle) -> BadService:
       service = BadService()
       
       async def bad_start():
           # This blocks the event loop!
           time.sleep(30)  # Should be await asyncio.sleep(30)
       
       lifecycle.append(Hook(on_start=bad_start))
       return service
   ```

### Type Annotation Issues

#### Error: MyPy type checking failures

**Symptoms:**
```bash
error: Argument 1 to "new_user_service" has incompatible type "DatabaseService"; expected "Database"
```

**Solutions:**

1. **Consistent Type Annotations**
   ```python
   # Problem: Inconsistent types
   def new_database() -> Database:  # Returns Database
       return Database()
   
   def new_user_service(db: DatabaseService) -> UserService:  # Expects DatabaseService
       return UserService(db)
   
   # Solution: Make types consistent
   def new_database() -> DatabaseService:  # Now consistent
       return DatabaseService()
   ```

2. **Use Protocols for Interface Types**
   ```python
   from typing import Protocol
   
   class DatabaseProtocol(Protocol):
       async def execute(self, query: str) -> Any: ...
       async def fetch_all(self, query: str) -> List[dict]: ...
   
   def new_user_service(db: DatabaseProtocol) -> UserService:
       # Accepts any object implementing the protocol
       return UserService(db)
   ```

3. **Generic Type Variables**
   ```python
   from typing import TypeVar, Generic
   
   T = TypeVar('T')
   
   class Repository(Generic[T]):
       def __init__(self, db: DatabaseService):
           self.db = db
   
   def new_user_repository(db: DatabaseService) -> Repository[User]:
       return Repository[User](db)
   ```

### Configuration Issues

#### Error: Configuration validation failures

**Symptoms:**
```python
ValueError: Database password is required
```

**Debug Steps:**

1. **Add Configuration Debugging**
   ```python
   @dataclass
   class DatabaseConfig:
       host: str
       port: int
       password: str
       
       @classmethod
       def from_env(cls):
           config = cls(
               host=os.getenv("DB_HOST", "localhost"),
               port=int(os.getenv("DB_PORT", "5432")),
               password=os.getenv("DB_PASSWORD", ""),
           )
           
           # Debug configuration
           logger.info(f"Database config: host={config.host}, port={config.port}")
           logger.info(f"Password provided: {'Yes' if config.password else 'No'}")
           
           return config
   ```

2. **Environment Variable Debugging**
   ```python
   import os
   
   def debug_environment():
       """Print all environment variables for debugging"""
       for key, value in os.environ.items():
           if 'PASSWORD' in key or 'SECRET' in key:
               logger.info(f"{key}=<redacted>")
           else:
               logger.info(f"{key}={value}")
   
   # Call before creating config
   debug_environment()
   config = DatabaseConfig.from_env()
   ```

3. **Default Value Issues**
   ```python
   # Problem: Default values that don't work in production
   @dataclass
   class AppConfig:
       debug: bool = True  # Should be False by default
       secret_key: str = "dev-key"  # Insecure default
   
   # Solution: Environment-aware defaults
   @dataclass
   class AppConfig:
       debug: bool = False
       secret_key: Optional[str] = None
       
       @classmethod
       def from_env(cls):
           config = cls(
               debug=os.getenv("DEBUG", "false").lower() == "true",
               secret_key=os.getenv("SECRET_KEY"),
           )
           
           # Validate in production
           if not config.debug and not config.secret_key:
               raise ValueError("SECRET_KEY is required in production")
           
           return config
   ```

### Testing Issues

#### Error: Tests fail with dependency injection

**Symptoms:**
```python
AttributeError: 'AsyncMock' object has no attribute 'some_method'
```

**Solutions:**

1. **Proper Mock Setup**
   ```python
   # Problem: Mock doesn't match interface
   mock_db = AsyncMock()  # Generic mock
   
   # Solution: Specify the spec
   mock_db = AsyncMock(spec=DatabaseService)
   
   # Or create a proper mock
   mock_db = AsyncMock(spec=DatabaseService)
   mock_db.get_user.return_value = User(id="123", name="Test")
   ```

2. **Test Configuration**
   ```python
   @pytest.fixture
   async def test_app():
       # Use test-specific configuration
       test_config = DatabaseConfig(
           host="localhost",
           port=5432,
           password="test-password",  # Don't use empty password in tests
       )
       
       app = TestApp(
           Provide(new_database_service, new_user_service),
           Supply(test_config),
       )
       
       async with app:
           yield app
   ```

3. **Async Test Setup**
   ```python
   # Problem: Not awaiting async operations
   @pytest.mark.asyncio
   async def test_user_service():
       service = create_user_service()
       user = service.get_user("123")  # Missing await!
       assert user.name == "Test"
   
   # Solution: Await async operations
   @pytest.mark.asyncio
   async def test_user_service():
       service = create_user_service()
       user = await service.get_user("123")  # Add await
       assert user.name == "Test"
   ```

## Performance Issues

### Slow Application Startup

**Symptoms:**
- Application takes too long to start
- Users experience timeout during deployment

**Debug and Optimize:**

1. **Measure Startup Time**
   ```python
   import time
   from di_fx.profiling import startup_profiler
   
   @startup_profiler
   def new_slow_service() -> SlowService:
       # This will measure and log creation time
       return SlowService()
   ```

2. **Lazy Loading Heavy Dependencies**
   ```python
   # Problem: Loading ML model during startup
   def new_ml_service() -> MLService:
       model = load_huge_ml_model()  # 5GB model, takes 30 seconds
       return MLService(model)
   
   # Solution: Lazy loading
   class MLService:
       def __init__(self):
           self._model = None
       
       async def get_model(self):
           if self._model is None:
               self._model = await load_huge_ml_model_async()
           return self._model
   
   def new_ml_service() -> MLService:
       return MLService()  # Fast startup, load on demand
   ```

3. **Parallel Initialization**
   ```python
   # Problem: Sequential initialization
   async def start_all_services():
       await service_a.start()  # 5 seconds
       await service_b.start()  # 5 seconds
       await service_c.start()  # 5 seconds
       # Total: 15 seconds
   
   # Solution: Parallel where possible
   async def start_all_services():
       await asyncio.gather(
           service_a.start(),
           service_b.start(),
           service_c.start(),
       )
       # Total: 5 seconds (if independent)
   ```

### Memory Leaks

**Symptoms:**
- Memory usage grows over time
- Application becomes sluggish
- Eventually crashes with OOM

**Debug Steps:**

1. **Check Resource Cleanup**
   ```python
   # Problem: Not cleaning up resources
   async def new_leaky_service() -> AsyncIterator[LeakyService]:
       connection = await create_connection()
       service = LeakyService(connection)
       
       yield service
       
       # Missing cleanup!
       # Should have: await connection.close()
   
   # Solution: Proper cleanup
   async def new_clean_service() -> AsyncIterator[CleanService]:
       connection = await create_connection()
       service = CleanService(connection)
       
       try:
           yield service
       finally:
           await connection.close()  # Proper cleanup
   ```

2. **Monitor Resource Usage**
   ```python
   import psutil
   import asyncio
   
   async def monitor_memory():
       while True:
           process = psutil.Process()
           memory_mb = process.memory_info().rss / 1024 / 1024
           logger.info(f"Memory usage: {memory_mb:.1f} MB")
           await asyncio.sleep(60)
   
   # Start monitoring
   asyncio.create_task(monitor_memory())
   ```

3. **Use Weak References for Caches**
   ```python
   import weakref
   
   class CacheService:
       def __init__(self):
           # Use WeakValueDictionary to prevent memory leaks
           self._cache = weakref.WeakValueDictionary()
       
       def get(self, key: str):
           return self._cache.get(key)
       
       def set(self, key: str, value):
           self._cache[key] = value
   ```

## Debugging Tools

### Enable Debug Logging

```python
import logging

# Enable debug logging for di_fx
logging.getLogger("di_fx").setLevel(logging.DEBUG)

# Add detailed handler
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logging.getLogger("di_fx").addHandler(handler)
```

### Dependency Graph Visualization

```python
def debug_dependency_graph(app: App):
    """Print detailed dependency information"""
    print("Dependency Graph:")
    print("================")
    
    for service_type, provider in app._providers.items():
        print(f"\n{service_type.__name__}:")
        
        # Show dependencies
        dependencies = get_function_dependencies(provider)
        for dep in dependencies:
            print(f"  → {dep.__name__}")
        
        # Show lifecycle hooks
        if hasattr(provider, '_lifecycle_hooks'):
            print(f"  Lifecycle: {len(provider._lifecycle_hooks)} hooks")

# Usage
app = create_app()
debug_dependency_graph(app)
```

### Performance Profiling

```python
import cProfile
import pstats
from di_fx.profiling import profile_startup

@profile_startup
async def main():
    app = create_app()
    await app.run()

# This will generate a performance report showing:
# - Time spent in each constructor function
# - Memory allocation patterns
# - Bottleneck identification
```

## Getting Help

### Reporting Issues

When reporting issues, include:

1. **Environment Information**
   ```python
   import sys
   import di_fx
   
   print(f"Python version: {sys.version}")
   print(f"di_fx version: {di_fx.__version__}")
   print(f"Platform: {sys.platform}")
   ```

2. **Minimal Reproduction**
   ```python
   # Create the smallest possible example that reproduces the issue
   from di_fx import App, Provide
   
   def new_broken_service() -> BrokenService:
       # This should demonstrate the problem
       return BrokenService()
   
   async def main():
       app = App(Provide(new_broken_service))
       await app.run()
   
   if __name__ == "__main__":
       asyncio.run(main())
   ```

3. **Full Error Messages**
   ```bash
   # Include the complete stack trace
   Traceback (most recent call last):
     File "main.py", line 10, in main
       await app.run()
     # ... complete stack trace
   ```

4. **Configuration Details**
   - Operating system and version
   - Python version and virtual environment
   - Relevant environment variables (sanitized)
   - External service versions (PostgreSQL, Redis, etc.)

### Community Resources

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share patterns
- **Stack Overflow**: Use tags `python`, `dependency-injection`, `di-fx`
- **Documentation**: Check examples and API reference

This troubleshooting guide should help you diagnose and resolve the most common issues when working with di_fx.