# Contributing to Kubeflow Pipelines Components

Welcome! This guide covers everything you need to know to contribute components and pipelines to this repository.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Setup](#quick-setup)
- [What We Accept](#what-we-accept)
- [Component Structure](#component-structure)
- [Naming Conventions](#naming-conventions)
- [Development Workflow](#development-workflow)
- [Testing and Quality](#testing-and-quality)
- [Submitting Your Contribution](#submitting-your-contribution)
- [Getting Help](#getting-help)

## Prerequisites

Before contributing, ensure you have the following tools installed:

- **Python 3.11+** for component development
- **uv** ([installation guide](https://docs.astral.sh/uv/getting-started/installation)) to manage Python dependencies including `kfp` and `kfp-kubernetes` packages
- **pre-commit** ([installation guide](https://pre-commit.com/#installation)) for automated code quality checks
- **Docker or Podman** to build container images for custom components
- **kubectl** ([installation guide](https://kubernetes.io/docs/tasks/tools/)) for Kubernetes operations

All contributors must follow the [Kubeflow Community Code of Conduct](https://github.com/kubeflow/community/blob/master/CODE_OF_CONDUCT.md).

## Quick Setup

### Installing uv

This project uses `uv` for fast Python package management.

Follow the installation instructions at: <https://docs.astral.sh/uv/getting-started/installation/>

Verify installation:

```bash
uv --version
```

### Setting Up Your Environment

Get your development environment ready with these commands:

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/pipelines-components.git
cd pipelines-components
git remote add upstream https://github.com/kubeflow/pipelines-components.git

# Set up Python environment
uv venv
source .venv/bin/activate
uv sync          # Installs package in editable mode
uv sync --dev    # Include dev dependencies if defined

# Install pre-commit hooks for automatic code quality checks
pre-commit install

# Verify your setup works
pytest
```

### Building Packages

```bash
uv build
```

### Installing and Testing the Built Package

After building, you can install and test the wheel locally:

```bash
# Install the built wheel
uv pip install dist/kfp_components-*.whl

# Test imports work correctly
python -c "from kfp_components import components, pipelines; print('Core package imports OK')"
```

## What We Accept

We welcome contributions of production-ready ML components and re-usable pipelines:

- **Components** are individual ML tasks (data processing, training, evaluation, deployment)
- **Pipelines** are complete multi-step workflows that can be nested within other pipelines
- **Bug fixes** improve existing components or fix documentation issues

## Component Structure

Components must be organized by category under `components/<category>/`.

Pipelines must be organized by category under `pipelines/<category>/`.

## Naming Conventions

- **Components and pipelines** use `snake_case` (e.g., `data_preprocessing`, `model_trainer`)
- **Commit messages** follow [Conventional Commits](https://conventionalcommits.org/) format with type prefix (feat, fix, docs, etc.)

### Required Files

Every component must include these files in its directory:

```text
components/<category>/<component_name>/
├── __init__.py            # Exposes the component function for imports
├── component.py           # Main implementation
├── metadata.yaml          # Complete specification (see schema below)
├── README.md              # Overview, inputs/outputs, usage examples, development instructions
├── OWNERS                 # Maintainers (approvers must be Kubeflow community members)
├── Containerfile          # Container definition (optional; required only when using a custom image)
├── example_pipelines.py   # Working usage examples (optional)
└── tests/
│   └── test_component.py  # Unit tests (optional)
└── <supporting_files>
```

Similarly, every pipeline must include these files:

```text
pipelines/<category>/<pipeline_name>/
├── __init__.py            # Exposes the pipeline function for imports
├── pipeline.py            # Main implementation
├── metadata.yaml          # Complete specification (see schema below)
├── README.md              # Overview, inputs/outputs, usage examples, development instructions
├── OWNERS                 # Maintainers (approvers must be Kubeflow community members)
├── example_pipelines.py   # Working usage examples (optional)
└── tests/
│   └── test_pipeline.py  # Unit tests (optional)
└── <supporting_files>
```

### metadata.yaml Schema

Your `metadata.yaml` must include these fields:

```yaml
name: my_component
stability: stable  # 'alpha', 'beta', or 'stable'
dependencies:
  kubeflow:
    - name: Pipelines
      version: '>=2.5'
  external_services:  # Optional list of external dependencies
    - name: Argo Workflows
      version: "3.6"
tags:  # Optional keywords for discoverability
  - training
  - evaluation
lastVerified: 2025-11-18T00:00:00Z  # Updated annually; components are removed after 12 months without update
ci:
  compile_check: true  # Validates component compiles with kfp.compiler
  skip_dependency_probe: false   # Optional. Set true only with justification
  pytest: optional
links:  # Optional, can use custom key-value (not limited to documentation, issue_tracker)
  documentation: https://kubeflow.org/components/my_component
  issue_tracker: https://github.com/kubeflow/pipelines-components/issues
```

### OWNERS File

The OWNERS file enables component owners to self-service maintenance tasks including approvals, metadata updates, and lifecycle management:

```yaml
approvers:
  - maintainer1  # Approvers must be Kubeflow community members
  - maintainer2
reviewers:
  - reviewer1
```

The `OWNERS` file enables code review automation by leveraging PROW commands:

- **Reviewers** (as well as **Approvers**), upon reviewing a PR and finding it good to merge, can comment `/lgtm`, which applies the `lgtm` label to the PR
- **Approvers** (but not **Reviewers**) can comment `/approve`, which signifies the PR is approved for automation to merge into the repo.
- If a PR has been labeled with both `lgtm` and `approve`, and all required CI checks are passing, PROW will merge the PR into the destination branch.

See [full Prow documentation](https://docs.prow.k8s.io/docs/components/plugins/approve/approvers/#lgtm-label) for usage details.

## Development Workflow

### 1. Create Your Feature Branch

Start by syncing with upstream and creating a feature branch:

```bash
git remote add upstream https://github.com/kubeflow/pipelines-components.git  # if not already set
git fetch upstream
git checkout -b component/my-component upstream/main
```

### 2. Implement Your Component

Create your component following the structure above. Here's a basic template:

```python
# component.py
from kfp import dsl

@dsl.component(base_image="python:3.11")
def hello_world(name: str = "World") -> str:
    """A simple hello world component.
    
    Args:
        name: The name to greet. Defaults to "World".
        
    Returns:
        A greeting message.
    """
    message = f"Hello, {name}!"
    print(message)
    return message
```

Write comprehensive tests for your component:

```python
# tests/test_component.py
from ..component import hello_world

def test_hello_world_default():
    """Test hello_world with default parameter."""
    # Access the underlying Python function from the component
    result = hello_world.python_func()
    assert result == "Hello, World!"


def test_hello_world_custom_name():
    """Test hello_world with custom name."""
    result = hello_world.python_func(name="Kubeflow")
    assert result == "Hello, Kubeflow!"
```

### 3. Document Your Component

This repository requires a standardized README.md. As such, we have provided a README generation utility, which can be found in the `scripts` directory.

Read more in the [README Generator Script Documentation](./scripts/generate_readme/README.md).

## Testing and Quality

### Running Tests Locally

Run these commands from your component/pipeline directory before submitting your contribution:

```bash
# Run all unit tests with coverage reporting
pytest --cov=src --cov-report=html

# Run specific test files when debugging
pytest tests/test_my_component.py -v
```

### Code Quality Checks

Ensure your code meets quality standards:

```bash
# Format checking (120 character line length)
black --check --line-length 120 .

# Docstring validation (Google convention)
pydocstyle --convention=google .

# Validate metadata schema
python scripts/validate_metadata.py

# Run all pre-commit hooks
pre-commit run --all-files
```

### Building Custom Container Images

If your component uses a custom image, test the container build:

```bash
# Build your component image
docker build -t my-component:test components/<category>/my-component/

# Test the container runs correctly
docker run --rm my-component:test echo "Hello, world!"
```

### CI Pipeline

GitHub Actions automatically runs these checks on every pull request:

- Code formatting (Black), linting (Flake8), docstring validation (pydocstyle), type checking (MyPy)
- Unit and integration tests with coverage reporting
- Container image builds for components with Containerfiles
- Security vulnerability scans
- Metadata schema validation
- Standardized README content and formatting conformance

## Submitting Your Contribution

### Commit Your Changes

Use descriptive commit messages following the [Conventional Commits](https://conventionalcommits.org/) format:

```bash
git add .
git status  # Review what you're committing
git diff --cached  # Check the actual changes

git commit -m "feat(training): add <my_component> training component

- Implements <my_component> component
- Includes comprehensive unit tests with 95% coverage
- Provides working pipeline examples
- Resolves #123"
```

### Push and Create Pull Request

Push your changes and create a pull request on GitHub:

```bash
git push origin component/my-component
```

On GitHub, click "Compare & pull request" and fill out the PR template provided with appropriate details

All PRs must pass:

- Automated checks (linting, tests, builds)
- Code review by maintainers and community members
- Documentation review

### Review Process

All pull requests must complete the following:

- All Automated CI checks successfully passing
- Code Review - reviewers will verify the following:
  - Component works as described
  - Code is clean and well-documented
  - Included tests provide good coverage.
- Receive approval from component OWNERS (for updates to existing components) or repository maintainers (for new components)

## Getting Help

- **Governance questions**: See [GOVERNANCE.md](GOVERNANCE.md) for ownership, verification, and process details
- **Community discussion**: Join `#kubeflow-pipelines` channel on the [CNCF Slack](https://www.kubeflow.org/docs/about/community/#kubeflow-slack-channels)
- **Bug reports and feature requests**: Open an issue at [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues)

---

This repository was established through [KEP-913: Components Repository](https://github.com/kubeflow/community/tree/master/proposals/913-components-repo).

Thanks for contributing to Kubeflow! 🚀
