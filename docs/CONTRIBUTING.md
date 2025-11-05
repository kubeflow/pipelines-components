# Contributing to Kubeflow Pipelines Components

Thank you for your interest in contributing to the Kubeflow Pipelines Components repository!

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Component Structure](#component-structure)
- [Development Workflow](#development-workflow)
- [Quality Standards](#quality-standards)
- [Submitting Changes](#submitting-changes)
- [Getting Help](#getting-help)

## Getting Started

Before contributing:

1. Review the repository structure in the [README](../README.md)
2. Review existing components and pipelines to understand the patterns
3. Check existing [issues](https://github.com/kubeflow/pipelines-components/issues) to avoid duplicate work
4. Join the [Kubeflow Slack](https://www.kubeflow.org/docs/about/community/) #kubeflow-pipelines channel

## Development Environment

### Installing uv

This project uses `uv` for fast Python package management.

Follow the installation instructions at: <https://docs.astral.sh/uv/getting-started/installation/>

Verify installation:

```bash
uv --version
```

### Setting Up Your Environment

```bash
# Clone and navigate to the repository
cd pipelines-components

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync          # Installs package in editable mode
uv sync --dev    # Include dev dependencies if defined
```

### Building Packages

```bash
# Build core package
uv build

# Build third-party package
cd third_party && uv build && cd ..
```

## Component Structure

Each component or pipeline must follow this structure:

```text
components/
└── <category>/
    └── <component-name>/
        ├── __init__.py          # Exposes component for imports
        ├── component.py         # Component implementation
        ├── metadata.yaml        # Component metadata (required)
        ├── README.md            # Documentation (auto-generated + custom)
        ├── OWNERS               # Component owners (required)
        ├── example_pipelines.py # Usage examples (required for components)
        ├── requirements.txt     # Runtime dependencies (if any)
        ├── Containerfile        # Custom base image (if needed)
        └── tests/
            └── test_component.py
```

### Required Files

#### metadata.yaml

```yaml
tier: core  # or third_party
name: my_component
stability: alpha  # alpha, beta, or stable
dependencies:
  kubeflow:
    - name: Pipelines
      version: '>=2.5'
  external_services:
    - name: BigQuery
      version: "latest"
tags:
  - training
  - tensorflow
lastVerified: 2025-01-15T00:00:00Z
ci:
  skip_dependency_probe: false
  pytest: optional
links:
  documentation: https://kubeflow.org/components/my_component
  issue_tracker: https://github.com/kubeflow/pipelines-components/issues
```

#### OWNERS

Follow the Kubernetes OWNERS file format:

```yaml
# See the OWNERS docs at https://go.k8s.io/owners

approvers:
  - username1
  - username2
  - kubeflow/sig-pipelines

reviewers:
  - username1
  - username2
  - username3
```

#### component.py

```python
"""Component for training a model."""

from kfp import dsl

@dsl.component(
    packages_to_install=["pandas==2.2.1"],  # Or use requirements.txt
    base_image="python:3.10-slim"
)
def my_component(
    input_path: str,
    output_path: str,
    learning_rate: float = 0.001
) -> str:
    """
    Train a model with the given parameters.
    
    Args:
        input_path: Path to input data
        output_path: Path to save the model
        learning_rate: Learning rate for training
        
    Returns:
        Path to the trained model
    """
    # Component implementation
    return output_path
```

> **Note**: Component runtime dependencies can be specified either in `requirements.txt` or via `packages_to_install` in the decorator.

## Development Workflow

### 1. Write Your Component

Follow the structure above and ensure all required files are present.

### 2. Format Your Code

```bash
black --line-length 120 path/to/your/files
```

### 3. Test Your Component

```bash
# Run your component tests
pytest path/to/your/component/tests/ --timeout=120

# Run all tests in a category
pytest components/training/ -v
```

### 4. Generate/Update Documentation

```bash
python scripts/generate_readme.py
```

Custom content after `<!-- custom-content -->` marker is preserved.

## Quality Standards

### Code Standards

- Black formatting with 120-character line length
- Google-style docstrings (enforced with `pydocstyle --convention=google`)
- Only stdlib imports at module top level; third-party imports inside functions

### Testing Standards

- Tests must be lightweight without cluster dependencies
- 2-minute timeout per test (enforced with `pytest-timeout`)

### Documentation Standards

- Every `@dsl.component` or `@dsl.pipeline` function must have docstrings
- READMEs are auto-generated from templates

## Submitting Changes

### Pre-submission Checklist

- [ ] Component follows the required structure
- [ ] All required files present (`metadata.yaml`, `OWNERS`, `README.md`)
- [ ] Code formatted with Black
- [ ] Tests pass locally
- [ ] Docstrings follow Google style
- [ ] `lastVerified` date is current
- [ ] README generated/updated

## Getting Help

See the [README](../README.md#-links) for community resources and support channels.
