# Best Practices Guide

## Overview

This guide covers proven patterns, common pitfalls, and architectural recommendations for building robust applications with di_fx. Following these practices will help you create maintainable, testable, and scalable systems.

## Constructor Function Design

### 1. Keep Constructor Functions Simple and Focused

✅ **Good: Single Responsibility**
```python
def new_user_service(db: DatabaseService, cache: CacheService) -> UserService:
    """Create user service with database and cache dependencies"""
    return UserService(db, cache)

def new_email_service(config: EmailConfig, logger: Logger) -> EmailService:
    """Create email service with configuration and logging"""
    return EmailService(config, logger)
```

❌ **Avoid: Complex Logic in Constructors**
```python
def new_user_service(db: DatabaseService, config: AppConfig) -> UserService:
    """DON'T: Too much logic in constructor"""
    
    # Complex initialization logic makes testing harder
    cache_config = CacheConfig(
        url=config.cache_url,
        timeout=config.cache_timeout,
        max_connections=calculate_pool_size(config.environment)
    )
    
    cache = CacheService(cache_config)
    email_sender = EmailSender(config.smtp_settings)
    
    # This should be separate constructor functions
    return UserService(db, cache, email_sender, config.feature_flags)
```

### 2. Use Clear Dependency Declaration

✅ **Good: Explicit Dependencies**
```python
def new_order_service(
    db: DatabaseService,
    payment_gateway: PaymentGateway,
    inventory: InventoryService,
    logger: Logger,
) -> OrderService:
    """Dependencies are explicit and easy to understand"""
    return OrderService(db, payment_gateway, inventory, logger)
```

❌ **Avoid: Hidden or Implicit Dependencies**
```python
def new_order_service() -> OrderService:
    """DON'T: Hidden dependencies make testing impossible"""
    # These dependencies are hidden - can't be mocked or replaced
    db = DatabaseService()  # How do we configure this?
    payment = PaymentGateway()  # What about testing?
    return OrderService(db, payment)
```

### 3. Prefer Composition Over Complex Inheritance

✅ **Good: Composition-Based Design**
```python
class UserService:
    def __init__(self, repository: UserRepository, validator: UserValidator):
        self.repository = repository
        self.validator = validator
    
    async def create_user(self, data: dict) -> User:
        # Validate using composed validator
        validated_data = await self.validator.validate(data)
        return await self.repository.create(validated_data)

def new_user_repository(db: DatabaseService) -> UserRepository:
    return SqlUserRepository(db)

def new_user_validator() -> UserValidator:
    return EmailUserValidator()

def new_user_service(
    repository: UserRepository, 
    validator: UserValidator
) -> UserService:
    return UserService(repository, validator)
```

❌ **Avoid: Complex Inheritance Hierarchies**
```python
class BaseService(ABC):
    """DON'T: Complex inheritance makes DI harder"""
    def __init__(self, db: DatabaseService, config: Config):
        self.db = db
        self.config = config

class UserService(BaseService):
    def __init__(self, db: DatabaseService, config: Config, cache: Cache):
        super().__init__(db, config)  # Hard to inject different implementations
        self.cache = cache
```

## Lifecycle Management Best Practices

### 1. Keep Lifecycle Hooks Simple

✅ **Good: Simple, Focused Hooks**
```python
def new_database_service(lifecycle: Lifecycle, config: DbConfig) -> DatabaseService:
    service = DatabaseService(config)
    
    # Simple, single-purpose hooks
    lifecycle.append(Hook(
        on_start=service.connect,
        on_stop=service.disconnect,
        timeout=30.0
    ))
    
    return service
```

❌ **Avoid: Complex Lifecycle Logic**
```python
def new_complex_service(lifecycle: Lifecycle) -> ComplexService:
    service = ComplexService()
    
    async def complex_startup():
        """DON'T: Too much logic in hooks"""
        # This should be broken down into service methods
        await service.initialize_database()
        await service.setup_monitoring()
        await service.register_health_checks()
        await service.start_background_workers()
        await service.announce_to_service_mesh()
    
    lifecycle.append(Hook(on_start=complex_startup))
    return service
```

### 2. Use AsyncIterator for Resource Management

✅ **Good: Resource Management with AsyncIterator**
```python
async def new_database_pool(config: DatabaseConfig) -> AsyncIterator[asyncpg.Pool]:
    """Automatic resource cleanup with AsyncIterator"""
    pool = await asyncpg.create_pool(config.dsn)
    try:
        # Test connection
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        
        yield pool
        
    finally:
        await pool.close()  # Automatic cleanup
```

❌ **Avoid: Manual Resource Management**
```python
def new_database_pool(lifecycle: Lifecycle, config: DatabaseConfig) -> DatabasePool:
    """DON'T: Manual resource management is error-prone"""
    pool = None
    
    async def setup():
        nonlocal pool
        pool = await asyncpg.create_pool(config.dsn)
        # What if this fails? Pool might not be set
    
    async def cleanup():
        if pool:  # Defensive programming needed
            await pool.close()
        # What if pool wasn't created successfully?
    
    lifecycle.append(Hook(on_start=setup, on_stop=cleanup))
    return pool  # This might be None!
```

### 3. Handle Errors Gracefully

✅ **Good: Comprehensive Error Handling**
```python
def new_resilient_service(
    lifecycle: Lifecycle,
    config: ServiceConfig,
    logger: Logger,
) -> ResilientService:
    service = ResilientService(config)
    
    async def start_with_retries():
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                await service.start()
                logger.info("Service started successfully")
                return
            except Exception as e:
                if attempt == max_attempts - 1:
                    logger.error(f"Service failed to start after {max_attempts} attempts")
                    raise
                
                wait_time = 2 ** attempt
                logger.warning(f"Start attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
    
    async def stop_gracefully():
        try:
            await asyncio.wait_for(service.stop(), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning("Graceful stop timed out, forcing shutdown")
            await service.force_stop()
        except Exception as e:
            # Don't raise during shutdown - log and continue
            logger.error(f"Error during shutdown: {e}")
    
    lifecycle.append(Hook(
        on_start=start_with_retries,
        on_stop=stop_gracefully,
    ))
    
    return service
```

## Configuration Management

### 1. Use Typed Configuration Classes

✅ **Good: Structured Configuration**
```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_mode: str = "require"
    pool_size: int = 10
    
    @classmethod
    def from_env(cls):
        """Load configuration from environment variables"""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "myapp"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            ssl_mode=os.getenv("DB_SSL_MODE", "require"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        )
    
    def validate(self) -> None:
        """Validate configuration values"""
        if not self.password:
            raise ValueError("Database password is required")
        if self.pool_size < 1:
            raise ValueError("Pool size must be at least 1")

@dataclass
class AppConfig:
    debug: bool = False
    log_level: str = "INFO"
    secret_key: Optional[str] = None
    
    @classmethod
    def from_env(cls):
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            secret_key=os.getenv("SECRET_KEY"),
        )
    
    def validate(self) -> None:
        if not self.debug and not self.secret_key:
            raise ValueError("Secret key is required in production")
```

❌ **Avoid: Magic Strings and Scattered Configuration**
```python
def new_database_service() -> DatabaseService:
    """DON'T: Magic strings and scattered config"""
    
    # Configuration scattered throughout the code
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DATABASE_PORT", "5432"))  # Inconsistent naming
    db = os.getenv("POSTGRES_DB", "myapp")  # Different prefix
    
    # No validation, no type safety
    return DatabaseService(host, port, db)
```

### 2. Environment-Specific Configuration

✅ **Good: Environment-Aware Configuration**
```python
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class AppConfig:
    environment: Environment
    debug: bool
    
    @classmethod
    def from_env(cls):
        env = Environment(os.getenv("ENVIRONMENT", "development"))
        
        return cls(
            environment=env,
            debug=env in (Environment.DEVELOPMENT, Environment.TESTING),
        )

def create_app() -> App:
    config = AppConfig.from_env()
    
    providers = [new_user_service]
    
    # Environment-specific providers
    if config.environment == Environment.PRODUCTION:
        providers.extend([
            new_postgres_database,
            new_redis_cache,
            new_datadog_metrics,
        ])
    else:
        providers.extend([
            new_sqlite_database,
            new_memory_cache,
            new_console_metrics,
        ])
    
    return App(
        Provide(*providers),
        Supply(config),
    )
```

## Error Handling Patterns

### 1. Fail Fast During Startup

✅ **Good: Early Validation**
```python
def new_payment_service(config: PaymentConfig) -> PaymentService:
    # Validate configuration early
    config.validate()
    
    service = PaymentService(config)
    
    # Test critical dependencies during startup
    async def validate_startup():
        try:
            await service.test_connection()
        except Exception as e:
            raise RuntimeError(f"Payment service validation failed: {e}")
    
    lifecycle.append(Hook(on_start=validate_startup))
    return service
```

❌ **Avoid: Lazy Error Discovery**
```python
def new_payment_service(config: PaymentConfig) -> PaymentService:
    """DON'T: Errors discovered at runtime"""
    # No validation - errors found later during actual use
    return PaymentService(config)

class PaymentService:
    async def process_payment(self, amount):
        # Error discovered here, too late!
        if not self.config.api_key:
            raise ValueError("API key not configured")
```

### 2. Graceful Degradation

✅ **Good: Circuit Breaker Pattern**
```python
class ResilientEmailService:
    def __init__(self, primary: EmailGateway, fallback: EmailGateway):
        self.primary = primary
        self.fallback = fallback
        self.circuit_open = False
        self.failure_count = 0
        self.last_failure_time = None
    
    async def send_email(self, email: Email) -> bool:
        if not self.circuit_open:
            try:
                await self.primary.send(email)
                self.failure_count = 0  # Reset on success
                return True
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= 5:  # Circuit breaker
                    self.circuit_open = True
                    logger.warning("Email primary circuit opened, using fallback")
        
        # Use fallback
        try:
            await self.fallback.send(email)
            return True
        except Exception as e:
            logger.error(f"Both email services failed: {e}")
            return False

def new_resilient_email_service(
    primary: EmailGateway,
    fallback: EmailGateway,
) -> ResilientEmailService:
    return ResilientEmailService(primary, fallback)
```

## Testing Best Practices

### 1. Test Constructor Functions Independently

✅ **Good: Isolated Constructor Testing**
```python
@pytest.mark.asyncio
async def test_user_service_constructor():
    """Test that constructor wires dependencies correctly"""
    
    mock_db = AsyncMock(spec=DatabaseService)
    mock_cache = AsyncMock(spec=CacheService)
    
    # Test the constructor function directly
    service = new_user_service(mock_db, mock_cache)
    
    # Verify dependencies are wired correctly
    assert service.db is mock_db
    assert service.cache is mock_cache
    
    # Test that service methods use dependencies
    await service.get_user("123")
    mock_db.get_user.assert_called_once_with("123")
```

### 2. Use Test-Specific Configuration

✅ **Good: Test Configuration Override**
```python
@dataclass
class TestDatabaseConfig:
    """Configuration optimized for testing"""
    connection_string: str = "sqlite:///:memory:"
    pool_size: int = 1  # Single connection for tests
    echo_sql: bool = True  # Log SQL for debugging

@pytest.fixture
async def test_app():
    """Test app with overridden configuration"""
    
    app = TestApp(
        Provide(
            new_database_service,
            new_user_service,
        ),
        Supply(
            TestDatabaseConfig(),  # Test-specific config
        ),
    )
    
    async with app:
        yield app
```

### 3. Test Lifecycle Behavior

✅ **Good: Lifecycle Testing**
```python
@pytest.mark.asyncio
async def test_service_lifecycle():
    """Test that service starts and stops correctly"""
    
    lifecycle = Lifecycle()
    mock_service = Mock()
    mock_service.start = AsyncMock()
    mock_service.stop = AsyncMock()
    
    # Create service with lifecycle hooks
    service = new_background_service(lifecycle, mock_service)
    
    # Test startup
    await lifecycle.start()
    mock_service.start.assert_called_once()
    
    # Test shutdown
    await lifecycle.stop()
    mock_service.stop.assert_called_once()
```

## Performance Considerations

### 1. Lazy vs Eager Initialization

✅ **Good: Lazy Initialization for Heavy Resources**
```python
class ImageProcessingService:
    def __init__(self, config: ImageConfig):
        self.config = config
        self._ml_model = None  # Lazy load expensive ML model
    
    async def get_ml_model(self):
        """Lazy load ML model only when needed"""
        if self._ml_model is None:
            self._ml_model = await load_ml_model(self.config.model_path)
        return self._ml_model
    
    async def process_image(self, image_data: bytes) -> ProcessedImage:
        model = await self.get_ml_model()
        return await model.process(image_data)
```

✅ **Good: Eager Initialization for Critical Resources**
```python
async def new_database_pool(config: DatabaseConfig) -> AsyncIterator[DatabasePool]:
    """Eager initialization for database - fail fast if unavailable"""
    
    pool = await asyncpg.create_pool(config.dsn, **config.pool_options)
    
    # Test connection immediately - fail fast
    async with pool.acquire() as conn:
        await conn.execute("SELECT 1")
    
    try:
        yield DatabaseService(pool)
    finally:
        await pool.close()
```

### 2. Connection Pooling and Resource Management

✅ **Good: Proper Resource Pooling**
```python
@dataclass
class HttpClientConfig:
    timeout: float = 30.0
    max_connections: int = 100
    keepalive_timeout: float = 30.0

async def new_http_client(config: HttpClientConfig) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client with connection pooling"""
    
    limits = httpx.Limits(
        max_connections=config.max_connections,
        keepalive_expiry=config.keepalive_timeout,
    )
    
    timeout = httpx.Timeout(config.timeout)
    
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        yield client
```

## Security Best Practices

### 1. Secure Configuration Management

✅ **Good: Secure Secret Handling**
```python
import os
from pathlib import Path

@dataclass
class SecretConfig:
    database_password: str
    api_key: str
    jwt_secret: str
    
    @classmethod
    def from_env(cls):
        """Load secrets from environment or files"""
        
        # Prefer environment variables
        db_password = os.getenv("DB_PASSWORD")
        
        # Fallback to Docker secrets
        if not db_password:
            secret_file = Path("/run/secrets/db_password")
            if secret_file.exists():
                db_password = secret_file.read_text().strip()
        
        if not db_password:
            raise ValueError("Database password not found in environment or secrets")
        
        return cls(
            database_password=db_password,
            api_key=os.getenv("API_KEY", ""),
            jwt_secret=os.getenv("JWT_SECRET", ""),
        )
```

### 2. Input Validation

✅ **Good: Comprehensive Input Validation**
```python
from pydantic import BaseModel, validator
import re

class CreateUserRequest(BaseModel):
    email: str
    name: str
    age: int
    
    @validator('email')
    def validate_email(cls, v):
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v.strip()
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v

class UserService:
    async def create_user(self, request: CreateUserRequest) -> User:
        # Validation happens automatically via Pydantic
        validated_data = request.dict()
        return await self.repository.create(validated_data)
```

## Common Anti-Patterns to Avoid

### 1. Service Locator Anti-Pattern

❌ **Don't: Global Container Access**
```python
# DON'T DO THIS
global_container = Container()

class UserService:
    def __init__(self):
        # Service locator anti-pattern
        self.db = global_container.resolve(DatabaseService)
        self.cache = global_container.resolve(CacheService)
    
    async def get_user(self, user_id: str):
        # Dependencies are hidden, testing is hard
        return await self.db.get_user(user_id)
```

✅ **Do: Explicit Dependency Injection**
```python
class UserService:
    def __init__(self, db: DatabaseService, cache: CacheService):
        # Dependencies are explicit and testable
        self.db = db
        self.cache = cache
    
    async def get_user(self, user_id: str):
        return await self.db.get_user(user_id)
```

### 2. Over-injection

❌ **Don't: Constructor with Too Many Dependencies**
```python
class OrderService:
    def __init__(
        self,
        db: DatabaseService,
        payment: PaymentService,
        inventory: InventoryService,
        email: EmailService,
        sms: SMSService,
        logger: Logger,
        metrics: MetricsService,
        cache: CacheService,
        config: OrderConfig,
    ):
        # Too many dependencies indicate design problems
        pass
```

✅ **Do: Decompose Large Services**
```python
class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        payment: PaymentService,
        notifications: NotificationService,  # Composed service
    ):
        self.repository = repository
        self.payment = payment
        self.notifications = notifications

class NotificationService:
    """Compose multiple notification channels"""
    def __init__(self, email: EmailService, sms: SMSService):
        self.email = email
        self.sms = sms
```

### 3. Circular Dependencies

❌ **Don't: Circular Dependencies**
```python
# DON'T DO THIS - Circular dependency
class UserService:
    def __init__(self, order_service: OrderService):
        self.order_service = order_service

class OrderService:
    def __init__(self, user_service: UserService):  # Circular!
        self.user_service = user_service
```

✅ **Do: Break Circular Dependencies**
```python
# Option 1: Extract shared logic to a separate service
class UserOrderService:
    def __init__(self, user_repo: UserRepository, order_repo: OrderRepository):
        self.user_repo = user_repo
        self.order_repo = order_repo

# Option 2: Use events/messaging to decouple
class OrderService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def create_order(self, order_data):
        order = await self.create(order_data)
        # Notify other services via events
        await self.event_bus.publish(OrderCreated(order))
```

## Monitoring and Observability

### 1. Structured Logging

✅ **Good: Structured Logging with Context**
```python
import structlog

def new_logger(config: LogConfig) -> structlog.BoundLogger:
    """Create structured logger"""
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer() if config.debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, config.level.upper())
        ),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()

class UserService:
    def __init__(self, db: DatabaseService, logger: structlog.BoundLogger):
        self.db = db
        self.logger = logger.bind(service="user_service")
    
    async def get_user(self, user_id: str) -> Optional[User]:
        log = self.logger.bind(user_id=user_id)
        log.info("Fetching user")
        
        try:
            user = await self.db.get_user(user_id)
            if user:
                log.info("User found")
            else:
                log.info("User not found")
            return user
        except Exception as e:
            log.error("Failed to fetch user", error=str(e))
            raise
```

### 2. Metrics and Health Checks

✅ **Good: Comprehensive Monitoring**
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Application metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_database_connections', 'Active database connections')

class MonitoredUserService:
    def __init__(self, db: DatabaseService, metrics_registry):
        self.db = db
        self.metrics = metrics_registry
    
    async def get_user(self, user_id: str) -> Optional[User]:
        start_time = time.time()
        
        try:
            user = await self.db.get_user(user_id)
            REQUEST_COUNT.labels(method='GET', endpoint='/users', status='success').inc()
            return user
        except Exception as e:
            REQUEST_COUNT.labels(method='GET', endpoint='/users', status='error').inc()
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)

def new_health_check_service(
    db: DatabaseService,
    cache: CacheService,
) -> HealthCheckService:
    """Health check service for monitoring"""
    return HealthCheckService({
        'database': db.health_check,
        'cache': cache.health_check,
    })
```

Following these best practices will help you build robust, maintainable applications with di_fx that scale well and are easy to test and debug.