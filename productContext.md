# Product Context: di_fx

## Problem Statement
Traditional Python dependency injection frameworks lack native async support, forcing developers to work around asyncio limitations. Existing solutions either don't support async operations properly, have poor performance characteristics, or require complex workarounds that don't integrate well with modern async Python frameworks like FastAPI, Django async views, and aiohttp.

## User Experience Goals
- **Seamless Async Integration**: Developers should be able to write async services without thinking about DI framework limitations
- **Performance First**: Dependency resolution should be fast enough that it's not a bottleneck in production applications
- **Framework Agnostic**: Easy integration with any async Python framework without vendor lock-in
- **Simple Mental Model**: Function-centric approach that's intuitive for Python developers
- **Production Ready**: Built-in lifecycle management, error handling, and observability

## Success Metrics
- **Performance**: 10-100x faster dependency resolution compared to existing frameworks
- **Memory Efficiency**: 70% less memory usage through smart caching
- **Framework Coverage**: Successful integration with FastAPI, Django, aiohttp, and Flask
- **Developer Experience**: Reduced boilerplate code and simpler testing patterns
- **Production Adoption**: Stable usage in production environments with graceful error handling
