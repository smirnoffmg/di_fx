.PHONY: help format lint check test clean install-dev

# Default target
help:
	@echo "Available commands:"
	@echo "  format     - Format code with ruff"
	@echo "  lint       - Run ruff linter"
	@echo "  check      - Run type checking with mypy"
	@echo "  test       - Run tests with pytest"
	@echo "  all        - Run format, lint, check, and test"
	@echo "  ci-test    - Test CI workflow locally"
	@echo "  install-dev - Install development dependencies"
	@echo "  clean      - Clean up cache and build files"

# Install development dependencies
install-dev:
	uv pip install -e ".[dev]"

# Format code
format:
	ruff format src/ tests/ examples/

# Run linter
lint:
	ruff check src/ tests/ examples/

# Fix linting issues automatically
lint-fix:
	ruff check --fix src/ tests/ examples/

# Run type checker
check:
	mypy src/

# Run tests
test:
	pytest tests/ -v

# Run all checks
all: format lint check test

# Clean up
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .mypy_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
