# Tech Context: di_fx

## Technologies Used
- **Python 3.12+**: Core language with async/await support
- **asyncio**: Native Python event loop for async operations
- **typing-extensions**: Enhanced type hints and annotations
- **hatchling**: Modern Python build system
- **pytest**: Testing framework with async support
- **mypy**: Static type checking
- **ruff**: Fast Python linter and formatter
- **coverage**: Code coverage measurement

## Development Setup
- **Package Manager**: uv for dependency management and virtual environments
- **Build System**: hatchling for wheel and source distribution
- **Code Quality**: ruff for linting and formatting, mypy for type checking
- **Testing**: pytest with asyncio support, coverage reporting
- **Documentation**: Markdown-based with potential for Sphinx/ReadTheDocs

## Technical Constraints
- **Python Version**: Requires Python 3.12+ for modern async features
- **Async-only**: Built specifically for asyncio, no synchronous fallbacks
- **Single Event Loop**: Designed for single-threaded async applications
- **Type Safety**: Strict mypy configuration with disallow_untyped_defs
- **Performance**: Must maintain 10-100x performance improvement over alternatives

## Dependencies
- **Core**: typing-extensions>=4.8.0
- **Development**: pytest, pytest-asyncio, pytest-cov, mypy, ruff
- **Optional**: Rust core for performance boost (di_fx[rust])
- **Framework Integrations**: FastAPI, Django, aiohttp, Flask (planned)

## Tool Usage Patterns
- **uv**: Primary tool for starting processes, managing dependencies, and virtual environments
- **pytest**: Async test execution with asyncio_mode=auto
- **ruff**: Combined linting and formatting with strict rules
- **mypy**: Strict type checking with comprehensive overrides for test modules
- **coverage**: HTML and XML coverage reports for quality assurance
