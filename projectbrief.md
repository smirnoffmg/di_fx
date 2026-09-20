# Project Brief: di_fx

## Overview
di_fx is a modern, async-first dependency injection framework for Python inspired by Uber-Fx. It provides a function-centric, event-loop native dependency injection system with superior performance and seamless async integration.

## Core Requirements
- Async-first architecture built for Python's asyncio event loop
- Function-centric approach without requiring classes or decorators
- Explicit dependency declaration through function parameters
- Comprehensive lifecycle management with startup/shutdown hooks
- Superior performance (10-100x faster than traditional frameworks)
- Framework integrations (FastAPI, Django, aiohttp, Flask)
- Production-ready with graceful startup/shutdown and error handling

## Goals
- Bring proven Uber-Fx patterns to Python with native async support
- Provide superior performance through smart caching and resource management
- Enable seamless integration with modern async Python frameworks
- Support large-scale applications with modular component organization
- Maintain zero threading overhead with cooperative concurrency

## Project Scope
**In Scope:**
- Core dependency injection framework
- Lifecycle management system
- Component organization and processing
- Framework integrations
- Testing utilities and overrides
- Performance optimization
- Error handling and validation
- Documentation and examples

**Out of Scope:**
- Synchronous-only applications
- Traditional class-based DI patterns
- Legacy Python version support (requires Python 3.12+)
- Non-async framework integrations
