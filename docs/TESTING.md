# Testing and Code Quality

This guide covers testing and code quality standards for the Kubeflow Pipelines Components Repository.

## Table of Contents

- [Code Quality Tools](#code-quality-tools)
- [Testing](#testing)
- [Configuration](#configuration)
- [Before Submitting](#before-submitting)
- [CI Pipeline](#ci-pipeline)
- [Getting Help](#getting-help)

## Code Quality Tools

*Essential linting and formatting tools required for all contributions.*

All code must pass these checks before being merged:

### Formatting and Linting

```bash
# Format Python code
black .

# Check code style
flake8 .

# Check docstrings
pydocstyle .

# Type checking
mypy .

# Lint markdown
markdownlint "**/*.md"
```

### Run All Checks

```bash
# Create and run lint script
cat > scripts/lint.sh << 'EOF'
#!/bin/bash
set -e
black --check .
flake8 .
pydocstyle .
mypy .
markdownlint "**/*.md"
echo "All checks passed!"
EOF

chmod +x scripts/lint.sh
./scripts/lint.sh
```

## Testing

*Comprehensive testing requirements including unit, integration, and component tests.*

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage (minimum 80% required)
pytest --cov=src --cov-report=html

# Run specific tests
pytest tests/test_my_component.py -v
```

### Integration Tests

```bash
# Set up test cluster
kind create cluster --name kfp-test

# Run integration tests
pytest tests/integration/

# Clean up
kind delete cluster --name kfp-test
```

### Component Tests

```bash
# Build and test component
docker build -t my-component:test components/my-component/
pytest tests/components/test_my_component.py
```

## Configuration

*Setup files and configurations for testing tools and pre-commit hooks.*

### pytest.ini

```ini
[tool:pytest]
testpaths = tests
addopts = --cov=src --cov-report=term-missing --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## Before Submitting

*Final checklist to ensure your code meets all quality and testing standards.*

Run this checklist before creating a pull request:

```bash
# 1. Format and lint
./scripts/lint.sh

# 2. Run tests
pytest --cov=src

# 3. Run pre-commit
pre-commit run --all-files

# 4. Build components
docker build -t test-component components/my-component/
```

## CI Pipeline

*Automated checks that run on every pull request to ensure code quality.*

Our GitHub Actions automatically run:
- Code quality checks (Black, Flake8, pydocstyle, MyPy)
- Unit and integration tests
- Container builds
- Security scans

## Getting Help

*Resources and support channels for testing and code quality questions.*

- Open a [GitHub Issue](https://github.com/kubeflow/pipelines-components/issues) for testing infrastructure problems
- Ask in [#kubeflow-pipelines Slack](https://kubeflow.slack.com/channels/kubeflow-pipelines)
- See [Contributing Guide](CONTRIBUTING.md) for more details

