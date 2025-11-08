# Contributor Onboarding Guide

Welcome to the Kubeflow Pipelines Components Repository! This guide will get you started as a contributor.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Setup](#quick-setup)
- [Development Workflow](#development-workflow)
- [Component Implementation](#component-implementation)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Documentation](#documentation)
- [Getting Help](#getting-help)
- [Next Steps](#next-steps)
- [References](#references)

## Prerequisites

*Essential tools and software needed before you can start contributing.*

Ensure you have these tools installed:

- **Python** (version 3.9+)
- **uv** - Fast Python package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation))
- **pre-commit** - Git hook framework for code quality ([installation guide](https://pre-commit.com/#installation))
- **Docker** or **Podman** to build container images
- **kubectl** - Kubernetes command-line tool ([installation guide](https://kubernetes.io/docs/tasks/tools/))

## Quick Setup

*Get your development environment ready in just a few commands.*

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/pipelines-components.git
cd pipelines-components
git remote add upstream https://github.com/kubeflow/pipelines-components.git

# Set up environment
uv venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Verify setup
./scripts/lint.sh
pytest
```

## Development Workflow

*Step-by-step process for developing and submitting components.*

### 1. Create Feature Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create branch
git checkout -b component/my-component
```

### 2. Develop Component or Pipeline

To create a component, follow the component structure:

```
components/my_component/   # or third_party/components/my_component
├── __init__.py            # (exposes the component entrypoint for imports)
├── component.py
├── metadata.yaml          # Component specification
├── README.md              # Documentation
├── OWNERS                 # Maintainers
├── Containerfile          # Container definition (required only for custom images)
├── example_pipelines.py
└── tests/
│   └── test_component.py  # Tests
└── <supporting_files>
```

To create a full example pipelines, follow the component structure:

```
pipelines/my_pipeline           # or third_party/pipelines/my_pipeline
├── README.md                   # (category index listing each pipeline with summaries/links)
├── __init__.py                 # (re-exports all pipelines in this category)
└── <pipeline-name>/
    ├── __init__.py             # (exposes the pipeline entrypoint)
    ├── pipeline.py             # Pipeline Definition
    ├── metadata.yaml           # Pipeline specification
    ├── README.md               # Documentation
    ├── OWNERS                  # Maintainers
    ├── tests/
    │   └── test_pipeline.py    # Tests  
    └── <supporting_files>
```


### 3. Test and Submit

```bash
# Test your changes
./scripts/lint.sh
pytest --cov=src

# Commit and push
git add .
git commit -m "feat: add my component"
git push origin component/my-component

# Create PR on GitHub
```

## Component Implementation

*Guidelines and examples for implementing components with proper structure.*

### Basic Structure

```python
# src/main.py
import argparse
import logging
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-data', type=str, required=True)
    parser.add_argument('--output-data', type=str, required=True)
    args = parser.parse_args()
    
    # Your component logic here
    process_data(args.input_data, args.output_data)

def process_data(input_path: str, output_path: str):
    """Process input data and save results."""
    # Implementation here
    pass

if __name__ == '__main__':
    main()
```

### metadata.yaml

```yaml
name: my_component
description: Brief description of what the component does
version: 1.0.0
inputs:
  - name: input_data
    type: Dataset
    description: Input dataset
outputs:
  - name: output_data
    type: Dataset
    description: Processed output
image: gcr.io/project/my-component:1.0.0
```

### Containerfile (required only for custom images)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY src/requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
ENTRYPOINT ["python", "main.py"]
```

## Testing

*How to write and run tests to ensure your component works correctly.*

Write comprehensive tests:

```python
# tests/test_main.py
import pytest
from src.main import process_data

def test_process_data():
    """Test basic functionality."""
    # Test implementation
    assert True  # Replace with actual tests

def test_error_handling():
    """Test error scenarios."""
    with pytest.raises(ValueError):
        process_data("invalid", "output")
```

## Code Quality

*Tools and standards for maintaining high code quality and consistency.*

For detailed testing and code quality guidelines, see [TESTING.md](TESTING.md).

### Quick Reference

```bash
# Format and lint
black .
flake8 .
pydocstyle .
mypy .

# Run all checks
./scripts/lint.sh

# Test with coverage
pytest --cov=src --cov-report=html
```

## Documentation

*Requirements for documenting your component clearly and comprehensively.*

Each component needs a comprehensive README.md with:

- **Overview**: What the component does
- **Inputs/Outputs**: Parameter specifications
- **Usage Examples**: How to use in pipelines
- **Development**: Build and test instructions

## Getting Help

*Resources and channels for getting support during your contribution journey.*

- **Setup Issues**: [ONBOARDING.md](ONBOARDING.md) (this guide)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Testing**: [TESTING.md](TESTING.md)
- **Governance**: [GOVERNANCE.md](GOVERNANCE.md)
- **Best Practices**: [BESTPRACTICES.md](BESTPRACTICES.md) *(coming soon)*
- **Agents**: [AGENTS.md](AGENTS.md) *(coming soon)*
- **Community**: [#kubeflow-pipelines Slack](https://kubeflow.slack.com/channels/kubeflow-pipelines)
- **Issues**: [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues) for bugs and questions

## Next Steps

*Recommended actions to take after completing the onboarding process.*

1. **Browse existing components** to understand patterns
2. **Check open issues** for contribution opportunities
3. **Join community meetings** to connect with maintainers
4. **Read the [Contributing Guide](CONTRIBUTING.md)** for detailed processes

---

## References

This repository was established through [KEP-913: Components Repository](https://github.com/kubeflow/community/tree/master/proposals/913-components-repo).

Ready to contribute? Start by exploring the repository and joining our community discussions!
