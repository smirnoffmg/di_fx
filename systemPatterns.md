# System Patterns: di_fx

## System Architecture
di_fx follows a layered, component-based architecture with clear separation of concerns:

- **Component Layer**: High-level application composition using `Component`, `Provide`, and `Supply`
- **Processing Layer**: `ComponentProcessor` and `ComponentProcessorManager` handle component execution
- **Resolution Layer**: `DependencyResolver` manages dependency graph and resolution
- **Lifecycle Layer**: `LifecycleManager` orchestrates startup/shutdown sequences
- **Execution Layer**: `InvokableExecutor` handles async function execution
- **Utility Layer**: Error handling, validation, state management, and observability

## Key Technical Decisions
- **Async-first design**: Built specifically for Python's asyncio event loop, avoiding threading overhead
- **Function-centric approach**: Inspired by Uber-Fx, using constructor functions instead of classes/decorators
- **Explicit dependency declaration**: Dependencies declared through function parameters for clarity
- **Component composition**: Modular organization allowing large applications to be built from smaller components
- **Lifecycle hooks**: Built-in startup/shutdown orchestration with timeout and error handling

## Design Patterns in Use
- **Dependency Injection**: Core pattern for service composition and management
- **Factory Pattern**: Constructor functions create service instances
- **Builder Pattern**: Component composition through fluent API
- **Observer Pattern**: Lifecycle hooks for startup/shutdown events
- **Strategy Pattern**: Pluggable validation and error handling
- **Composite Pattern**: Components can contain other components

## Component Relationships
```
Component
├── Provide (service constructors)
├── Supply (configuration/values)
├── Invoke (startup actions)
└── Nested Components

ComponentProcessor
├── ComponentProcessorManager
├── DependencyResolver
├── LifecycleManager
└── InvokableExecutor

Error Handling
├── ErrorHandler
├── ValidationManager
└── StateManager
```

## Critical Implementation Paths
1. **Component Registration**: Components register services, configuration, and lifecycle hooks
2. **Dependency Resolution**: Builds dependency graph and resolves services in correct order
3. **Lifecycle Execution**: Orchestrates startup sequence, runs hooks, manages shutdown
4. **Service Resolution**: Resolves service instances with proper scoping and lifecycle management
5. **Error Handling**: Graceful error handling with dependency chain visualization
