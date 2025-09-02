# Framework Integration Guide

## FastAPI Integration

FastAPI is async-first, making it a perfect match for our event loop native DI.

### Basic Integration

```python
from fastapi import FastAPI, Depends, Request
from di_fx import EventLoopApp, Provide, Supply
from di_fx.integrations.fastapi import DIDepends, request_scope

# Set up DI container
di_app = EventLoopApp(
    Provide(
        new_database_service,
        new_user_service,
        new_auth_service,
    ),
    Supply(
        DatabaseConfig.from_env(),
        AuthConfig.from_env(),
    ),
)

# FastAPI app
fastapi_app = FastAPI()

# Middleware for DI lifecycle
@fastapi_app.middleware("http")
async def di_middleware(request: Request, call_next):
    """Integrate DI with FastAPI request lifecycle"""
    
    # Create request scope context
    async with request_scope():
        # Make DI container available to request
        request.state.di_container = di_app
        
        response = await call_next(request)
        return response

# Dependency injection helper
async def get_di_service(service_type: type, request: Request):
    """Get service from DI container with request scoping"""
    container = request.state.di_container
    return await container.resolve_scoped(service_type, scope="request")

# Route handlers with DI
@fastapi_app.get("/users/{user_id}")
async def get_user(
    user_id: str,
    user_service: UserService = Depends(lambda req: get_di_service(UserService, req)),
    auth_service: AuthService = Depends(lambda req: get_di_service(AuthService, req)),
):
    """Route handler with injected dependencies"""
    
    # Validate authentication (both services are request-scoped)
    await auth_service.validate_request()
    
    # Get user data
    user = await user_service.get_user(user_id)
    return user.to_dict()

# Application startup/shutdown
@fastapi_app.on_event("startup")
async def startup():
    """Start DI container with FastAPI"""
    await di_app.startup()

@fastapi_app.on_event("shutdown") 
async def shutdown():
    """Stop DI container with FastAPI"""
    await di_app.shutdown()
```

### Advanced FastAPI Integration with Custom Dependency Provider

```python
from di_fx.integrations.fastapi import DIProvider, Scoped, Singleton

class FastAPIDIProvider(DIProvider):
    """Enhanced DI provider for FastAPI"""
    
    def __init__(self, di_app: EventLoopApp):
        self.di_app = di_app
        super().__init__()
    
    async def get_service(self, service_type: type, scope: str = "request") -> Any:
        """Get service with automatic scope detection"""
        return await self.di_app.resolve_scoped(service_type, scope)
    
    def create_dependency(self, service_type: type, scope: str = "request"):
        """Create FastAPI dependency function"""
        async def dependency():
            return await self.get_service(service_type, scope)
        return dependency

# Set up provider
di_provider = FastAPIDIProvider(di_app)

# Clean dependency declarations
@fastapi_app.get("/dashboard")
async def dashboard(
    user_service: UserService = Depends(di_provider.dependency(UserService, scope="request")),
    analytics: AnalyticsService = Depends(di_provider.dependency(AnalyticsService, scope="singleton")),
    db: Database = Depends(di_provider.dependency(Database, scope="singleton")),
):
    """Multiple dependencies with different scopes"""
    
    user_data = await user_service.get_current_user()
    dashboard_data = await analytics.get_dashboard_data(user_data.id)
    
    return {
        "user": user_data.to_dict(),
        "analytics": dashboard_data,
        "timestamp": datetime.utcnow(),
    }
```

### WebSocket Support

```python
@fastapi_app.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
):
    """WebSocket with DI support"""
    await websocket.accept()
    
    # Create WebSocket-scoped context
    async with di_app.websocket_scope(client_id=client_id):
        # Get WebSocket-scoped services
        chat_service = await di_app.resolve_scoped(ChatService, scope="websocket")
        user_service = await di_app.resolve_scoped(UserService, scope="websocket")
        
        try:
            while True:
                data = await websocket.receive_text()
                message = await chat_service.process_message(data)
                await websocket.send_text(message)
                
        except WebSocketDisconnect:
            await chat_service.handle_disconnect()
```

## Django Integration

Django has async support, and our DI can integrate with both sync and async views.

### Django Integration Setup

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ... other apps
    'di_fx.integrations.django',
]

# DI Configuration
DI_FX_CONFIG = {
    'providers': [
        'myapp.di.new_database_service',
        'myapp.di.new_user_service',
        'myapp.di.new_email_service',
    ],
    'supplies': [
        'myapp.config.DatabaseConfig',
        'myapp.config.EmailConfig',
    ],
}

# di_fx/integrations/django/__init__.py
from django.apps import AppConfig
from di_fx import EventLoopApp

class DIFxConfig(AppConfig):
    """Django app config for DI integration"""
    
    name = 'di_fx.integrations.django'
    
    def ready(self):
        """Initialize DI container when Django starts"""
        from django.conf import settings
        
        # Create DI container
        providers = [import_string(p) for p in settings.DI_FX_CONFIG['providers']]
        supplies = [import_string(s)() for s in settings.DI_FX_CONFIG['supplies']]
        
        self.di_app = EventLoopApp(
            Provide(*providers),
            Supply(*supplies),
        )
        
        # Store globally accessible container
        from di_fx.integrations.django.container import set_global_container
        set_global_container(self.di_app)
```

### Django Views with DI

```python
# views.py
from django.http import JsonResponse
from django.views import View
from di_fx.integrations.django import inject, async_inject
import asyncio

class UserView(View):
    """Sync Django view with DI"""
    
    @inject(UserService)
    def get(self, request, user_service: UserService):
        """Sync view with injected service"""
        
        user_id = request.GET.get('user_id')
        
        # Run async operation in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            user = loop.run_until_complete(user_service.get_user(user_id))
            return JsonResponse(user.to_dict())
        finally:
            loop.close()

# Async Django view (Django 4.1+)
from django.http import JsonResponse
from django.views.generic import View
from asgiref.sync import async_to_sync

class AsyncUserView(View):
    """Async Django view with DI"""
    
    @async_inject(UserService, EmailService)
    async def get(self, request, user_service: UserService, email_service: EmailService):
        """Pure async view with injected services"""
        
        user_id = request.GET.get('user_id')
        
        # Both operations are naturally async
        user = await user_service.get_user(user_id)
        await email_service.send_welcome_email(user.email)
        
        return JsonResponse({
            "user": user.to_dict(),
            "email_sent": True,
        })

# Function-based views
from di_fx.integrations.django import get_service

async def user_detail_view(request, user_id):
    """Async function-based view"""
    
    # Manual service resolution
    user_service = await get_service(UserService)
    auth_service = await get_service(AuthService, scope="request")
    
    # Validate access
    await auth_service.validate_user_access(request.user.id, user_id)
    
    # Get user data
    user = await user_service.get_user(user_id)
    
    return JsonResponse(user.to_dict())
```

### Django Middleware Integration

```python
# middleware.py
from di_fx.integrations.django import request_scope
import asyncio

class DIRequestMiddleware:
    """Middleware for DI request scoping"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    async def __call__(self, request):
        """Process request with DI scoping"""
        
        # Create request-scoped context
        async with request_scope(request_id=id(request)):
            if asyncio.iscoroutinefunction(self.get_response):
                response = await self.get_response(request)
            else:
                response = self.get_response(request)
            
            return response
```

## aiohttp Integration

aiohttp is pure async, making it ideal for our event loop native approach.

### aiohttp Application Setup

```python
from aiohttp import web, ClientSession
from di_fx import EventLoopApp, Provide, Supply

async def create_app():
    """Create aiohttp app with DI integration"""
    
    # Set up DI container
    di_app = EventLoopApp(
        Provide(
            new_database_service,
            new_user_service,
            new_http_client,
        ),
        Supply(
            DatabaseConfig.from_env(),
            HttpConfig.from_env(),
        ),
    )
    
    # Start DI container
    await di_app.startup()
    
    # Create aiohttp app
    app = web.Application()
    
    # Store DI container in app
    app['di_container'] = di_app
    
    # Set up routes
    app.router.add_get('/users/{user_id}', get_user_handler)
    app.router.add_post('/users', create_user_handler)
    
    # Cleanup on shutdown
    async def cleanup_di(app):
        await app['di_container'].shutdown()
    
    app.on_cleanup.append(cleanup_di)
    
    return app

# Request handlers with DI
async def get_user_handler(request):
    """aiohttp handler with dependency injection"""
    
    # Get DI container from app
    di_container = request.app['di_container']
    
    # Resolve services for this request
    user_service = await di_container.resolve_scoped(UserService, scope="request")
    auth_service = await di_container.resolve_scoped(AuthService, scope="request")
    
    # Extract request data
    user_id = request.match_info['user_id']
    
    # Validate authorization
    token = request.headers.get('Authorization')
    await auth_service.validate_token(token)
    
    # Get user data
    user = await user_service.get_user(user_id)
    
    if user:
        return web.json_response(user.to_dict())
    else:
        return web.json_response({'error': 'User not found'}, status=404)

# Middleware for automatic DI scoping
@web.middleware
async def di_middleware(request, handler):
    """Middleware for request-scoped DI"""
    
    di_container = request.app['di_container']
    
    # Create request scope
    async with di_container.request_scope():
        response = await handler(request)
        return response
```

### aiohttp with Background Tasks

```python
async def create_app_with_background_tasks():
    """aiohttp app with DI-managed background tasks"""
    
    di_app = EventLoopApp(
        Provide(
            new_database_service,
            new_task_processor,
            new_metrics_collector,
        ),
        Supply(
            TaskConfig.from_env(),
        ),
    )
    
    await di_app.startup()
    
    app = web.Application()
    app['di_container'] = di_app
    
    # Background tasks are automatically managed by DI lifecycle
    # They start with the container and stop on shutdown
    
    return app

def new_task_processor(lifecycle: Lifecycle, db: DatabaseService) -> TaskProcessor:
    """Background task processor managed by DI"""
    
    processor = TaskProcessor(db)
    
    async def start_processor():
        # Start as event loop task
        processor.task = asyncio.create_task(processor.run_forever())
    
    async def stop_processor():
        # Graceful shutdown
        if processor.task:
            processor.task.cancel()
            try:
                await processor.task
            except asyncio.CancelledError:
                pass
    
    lifecycle.on_start(start_processor)
    lifecycle.on_stop(stop_processor)
    
    return processor
```

## Flask Integration (with Flask 2.0+ async support)

### Flask Async Integration

```python
from flask import Flask, request, jsonify
from di_fx import EventLoopApp, Provide, Supply
from di_fx.integrations.flask import FlaskDI, inject_async
import asyncio

# Create Flask app
app = Flask(__name__)

# Set up DI
di_app = EventLoopApp(
    Provide(
        new_database_service,
        new_user_service,
    ),
    Supply(
        DatabaseConfig.from_env(),
    ),
)

# Flask-DI integration
flask_di = FlaskDI(app, di_app)

@app.route('/users/<user_id>')
@inject_async(UserService)
async def get_user(user_id: str, user_service: UserService):
    """Async Flask route with DI"""
    
    user = await user_service.get_user(user_id)
    
    if user:
        return jsonify(user.to_dict())
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/users', methods=['POST'])
@inject_async(UserService, EmailService)
async def create_user(user_service: UserService, email_service: EmailService):
    """Create user with multiple injected services"""
    
    data = request.get_json()
    
    # Create user
    user = await user_service.create_user(data)
    
    # Send welcome email
    await email_service.send_welcome_email(user.email)
    
    return jsonify({
        'user': user.to_dict(),
        'email_sent': True,
    }), 201

# Application lifecycle
@app.before_first_request
async def startup():
    await di_app.startup()

@app.teardown_appcontext
async def shutdown(exception):
    # Request scope cleanup happens automatically
    pass

# App shutdown
import atexit
atexit.register(lambda: asyncio.run(di_app.shutdown()))
```

## Celery Integration

Background task processing with DI support.

### Celery Worker with DI

```python
from celery import Celery
from di_fx import EventLoopApp, Provide, Supply
from di_fx.integrations.celery import DITask, get_service
import asyncio

# Create Celery app
celery_app = Celery('myapp')

# DI container for workers
di_app = EventLoopApp(
    Provide(
        new_database_service,
        new_email_service,
        new_analytics_service,
    ),
    Supply(
        DatabaseConfig.from_env(),
        EmailConfig.from_env(),
    ),
)

class DITaskBase(DITask):
    """Base task class with DI support"""
    
    def __init__(self):
        super().__init__()
        self.di_container = di_app

@celery_app.task(base=DITaskBase)
async def send_email_task(user_id: str, template: str):
    """Async Celery task with DI"""
    
    # Resolve services for this task
    user_service = await get_service(UserService)
    email_service = await get_service(EmailService)
    
    # Get user data
    user = await user_service.get_user(user_id)
    
    # Send email
    await email_service.send_templated_email(
        to=user.email,
        template=template,
        context={'user': user.to_dict()}
    )
    
    return f"Email sent to {user.email}"

@celery_app.task(base=DITaskBase)
async def process_analytics_batch(batch_id: str):
    """Heavy processing task with DI"""
    
    db = await get_service(DatabaseService)
    analytics = await get_service(AnalyticsService)
    
    # Process batch
    events = await db.get_events_batch(batch_id)
    results = await analytics.process_events(events)
    
    # Store results
    await db.store_analytics_results(batch_id, results)
    
    return f"Processed {len(events)} events"

# Worker startup
@celery_app.on_after_configure.connect
def setup_di(sender, **kwargs):
    """Start DI container when worker starts"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(di_app.startup())
```

## SQLAlchemy Integration

Database ORM integration with async session management.

### SQLAlchemy Async Session Management

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from di_fx import EventLoopApp, Provide
from typing import AsyncIterator

async def new_database_engine(config: DatabaseConfig) -> AsyncIterator[AsyncEngine]:
    """Create database engine with lifecycle management"""
    
    engine = create_async_engine(
        config.database_url,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        echo=config.echo_sql,
    )
    
    try:
        # Test connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        yield engine
        
    finally:
        await engine.dispose()

async def new_database_session_factory(engine: AsyncEngine) -> sessionmaker:
    """Create session factory"""
    return sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

async def new_database_session(
    session_factory: sessionmaker,
) -> AsyncIterator[AsyncSession]:
    """Create request-scoped database session"""
    
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()

# Repository with injected session
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, user_data: dict) -> User:
        user = User(**user_data)
        self.session.add(user)
        await self.session.flush()  # Get ID without committing
        return user

# Service layer
def new_user_repository(session: AsyncSession) -> UserRepository:
    return UserRepository(session)

def new_user_service(repository: UserRepository) -> UserService:
    return UserService(repository)

# DI setup with proper scoping
di_app = EventLoopApp(
    Provide(
        new_database_engine,
        new_database_session_factory,
        new_database_session,  # Request-scoped
        new_user_repository,
        new_user_service,
    ),
    Supply(
        DatabaseConfig.from_env(),
    ),
)
```

## Pydantic Integration

Data validation and serialization with DI.

### Pydantic Model Factories

```python
from pydantic import BaseModel, validator
from di_fx import EventLoopApp, Provide

class UserCreateRequest(BaseModel):
    email: str
    name: str
    age: int
    
    @validator('email')
    def validate_email(cls, v, values, config, field, **kwargs):
        # Access DI services in validators
        email_validator = config.context.get('email_validator')
        if email_validator and not email_validator.is_valid(v):
            raise ValueError('Invalid email address')
        return v

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    age: int
    created_at: datetime
    
    class Config:
        # Allow DI context in model
        arbitrary_types_allowed = True

# Service that creates models with DI context
class UserModelFactory:
    def __init__(self, email_validator: EmailValidatorService):
        self.email_validator = email_validator
    
    def create_user_request(self, data: dict) -> UserCreateRequest:
        """Create Pydantic model with DI context"""
        
        context = {'email_validator': self.email_validator}
        return UserCreateRequest.parse_obj(data, context=context)
    
    def create_user_response(self, user: User) -> UserResponse:
        """Create response model"""
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            age=user.age,
            created_at=user.created_at,
        )

def new_user_model_factory(email_validator: EmailValidatorService) -> UserModelFactory:
    return UserModelFactory(email_validator)
```

## Framework Comparison: DI Integration Benefits

| Framework | Traditional DI | Event Loop Native di_fx |
|-----------|----------------|------------------------|
| **FastAPI** | Manual wiring, no scoping | Native async, request scoping, perfect integration |
| **Django** | Complex setup, sync/async issues | Seamless sync+async, middleware integration |
| **aiohttp** | Custom solutions needed | Natural fit, built-in lifecycle management |
| **Flask** | Limited async support | Full async support with Flask 2.0+ |
| **Celery** | No DI integration | Native async task support with DI |
| **SQLAlchemy** | Manual session management | Automatic session scoping and cleanup |

## Key Advantages of Event Loop Native Integration

### 1. **Natural Async Flow**
```python
# Everything flows naturally through the event loop
@app.get("/complex-operation")
async def complex_operation(
    user_service: UserService = DIDepends(),
    email_service: EmailService = DIDepends(),
    analytics: AnalyticsService = DIDepends(),
):
    # All services resolved asynchronously
    user = await user_service.get_current_user()
    await email_service.send_notification(user.email)
    await analytics.track_event("complex_operation", user.id)
    
    return {"status": "completed"}
```

### 2. **Perfect Request Scoping**
```python
# Request-scoped services automatically cleaned up
async with request_scope():
    # Services created for this request only
    db_session = await container.resolve(DatabaseSession)  # New session
    user_service = await container.resolve(UserService)    # Uses above session
    
    # Work with services...
    user = await user_service.create_user(data)
    
# Session automatically committed/rolled back and closed
```

### 3. **Zero Framework Overhead**
- No additional threads or processes
- No synchronization primitives
- No blocking operations
- Perfect resource efficiency

This event loop native approach makes di_fx the **ideal DI framework for modern Python applications**!