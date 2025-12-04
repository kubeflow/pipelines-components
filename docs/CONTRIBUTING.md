# Contributing to Kubeflow Pipelines Components

Welcome! This guide covers everything you need to know to contribute components and pipelines to this repository.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Setup](#quick-setup)
- [What We Accept](#what-we-accept)
- [Component Structure](#component-structure)
- [Development Workflow](#development-workflow)
- [Testing and Quality](#testing-and-quality)
- [Adding a Custom Base Image](#adding-a-custom-base-image)
- [Submitting Your Contribution](#submitting-your-contribution)
- [Getting Help](#getting-help)

## Prerequisites

Before contributing, ensure you have the following tools installed:

- **Python 3.10+** for component development
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
# Build core package
uv build

# Build third-party package
cd third_party && uv build && cd ..
```

### Installing and Testing the Built Package

After building, you can install and test the wheel locally:

```bash
# Install the built wheel
uv pip install dist/kfp_components-*.whl

# Test imports work correctly
python -c "from kubeflow.pipelines.components import components, pipelines; print('Core package imports OK')"

# For third-party package
uv pip install dist-third-party/kfp_components_third_party-*.whl
python -c "from kubeflow.pipelines.components.third_party import components, pipelines; print('Third-party package imports OK')"
```

## What We Accept

We welcome contributions of production-ready ML components and re-usable pipelines:

- **Components** are individual ML tasks (data processing, training, evaluation, deployment) with usage examples
- **Pipelines** are complete multi-step workflows that can be nested within other pipelines
- **Bug fixes** improve existing components or fix documentation issues

## Component Structure

Components must be organized by category under `components/<category>/` (Core tier) or `third_party/components/<category>/` (Third-Party tier).

Pipelines must be organized by category under `pipelines/<category>/` (Core tier) or `third_party/pipelines/<category>/` (Third-Party tier).

## Naming Conventions

- **Components and pipelines** use `snake_case` (e.g., `data_preprocessing`, `model_trainer`)
- **Commit messages** follow [Conventional Commits](https://conventionalcommits.org/) format with type prefix (feat, fix, docs, etc.)

### Required Files

Every component must include these files in its directory:

```
components/<category>/<component_name>/
├── __init__.py            # Exposes the component function for imports
├── component.py           # Main implementation
├── metadata.yaml          # Complete specification (see schema below)
├── README.md              # Overview, inputs/outputs, usage examples, development instructions
├── OWNERS                 # Maintainers (at least one Kubeflow SIG owner for Core tier)
├── Containerfile          # Container definition (required only for Core tier custom images)
├── example_pipelines.py   # Working usage examples
└── tests/
│   └── test_component.py  # Unit tests
└── <supporting_files>
```

Similarly, every pipeline must include these files:
```
pipelines/<category>/<pipeline_name>/
├── __init__.py            # Exposes the pipeline function for imports
├── pipeline.py            # Main implementation
├── metadata.yaml          # Complete specification (see schema below)
├── README.md              # Overview, inputs/outputs, usage examples, development instructions
├── OWNERS                 # Maintainers (at least one Kubeflow SIG owner for Core tier)
├── example_pipelines.py   # Working usage examples
└── tests/
│   └── test_pipeline.py  # Unit tests
└── <supporting_files>
```

### metadata.yaml Schema

Your `metadata.yaml` must include these fields:

```yaml
name: my_component
tier: core  # or 'third_party'
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
  pytest: optional  # Set to 'required' for Core tier
links:  # Optional, can use custom key-value (not limited to documentation, issue_tracker)
  documentation: https://kubeflow.org/components/my_component
  issue_tracker: https://github.com/kubeflow/pipelines-components/issues
```

### OWNERS File

The OWNERS file enables component owners to self-service maintenance tasks including approvals, metadata updates, and lifecycle management:

```yaml
approvers:
  - maintainer1  # At least one must be a Kubeflow SIG owner/team member for Core tier
  - maintainer2
reviewers:
  - reviewer1
```

The `OWNERS` file enables code review automation by leveraging PROW commands:
- **Reviewers** (as well as **Approvers**), upon reviewing a PR and finding it good to merge, can comment `/lgtm`, which applies the `lgtm` label to the PR
- **Approvers** (but not **Reviewers**) can comment `/approver`, which signfies the PR is approved for automation to merge into the repo.
- If a PR has been labeled with both `lgtm` and `approve`, and all required CI checks are passing, PROW will merge the PR into the destination branch.

See [full Prow documentation](https://docs.prow.k8s.io/docs/components/plugins/approve/approvers/#lgtm-label) for usage details.

## Development Workflow

### 1. Create Your Feature Branch

Start by syncing with upstream and creating a feature branch:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git checkout -b component/my-component
```

### 2. Implement Your Component

Create your component following the structure above. Here's a basic template:

```python
# component.py
from kfp import dsl

@dsl.component(base_image="python:3.10")
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

This repository requires a standardized README.md.   As such, we have provided a README Generation utility, which can be found in the `scripts` directory.

Read more in the [README Generator Script Documentation](./scripts/generate_readme/README.md)

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
docker run --rm my-component:test --help
```

### CI Pipeline

GitHub Actions automatically runs these checks on every pull request:

- Code formatting (Black), linting (Flake8), docstring validation (pydocstyle), type checking (MyPy)
- Unit and integration tests with coverage reporting
- Container image builds for components with Containerfiles
- Security vulnerability scans
- Metadata schema validation
- Standardized README content and formatting conformance

## Adding a Custom Base Image

Components that require specific dependencies beyond what's available in standard KFP images can use custom base images. This section explains how to add and maintain custom base images for your components.

### Overview

Custom base images are:
- Built automatically by CI on every push to `main` and on tags
- Published to `ghcr.io/kubeflow/pipelines-components-<name>`
- Tagged with `:main` for the latest main branch build, plus git SHA and ref tags

### Step 1: Create the Containerfile

Create a `Containerfile` in your component's directory:

```
components/
└── training/
    └── my_component/
        ├── Containerfile      # Your custom base image
        ├── component.py
        ├── metadata.yaml
        └── README.md
```

Example `Containerfile`:

```dockerfile
FROM python:3.11-slim

RUN pip install --no-cache-dir \
    numpy==1.26.0 \
    pandas==2.1.0 \
    scikit-learn==1.3.0

WORKDIR /app
```

**Guidelines:**
- Keep images minimal - only include dependencies your component needs
- Pin dependency versions for reproducibility
- Use official base images when possible
- Avoid including secrets or credentials

### Step 2: Add Entry to the Workflow Matrix

Edit `.github/workflows/container-build.yml` and add your image to the matrix:

```yaml
strategy:
  matrix:
    include:
      # Existing entries...
      
      # Add your new image:
      - name: my-training-component
        containerfile: components/training/my_component/Containerfile
        context: components/training/my_component
```

**Matrix fields:**

| Field           | Description                                                                                              |
|-----------------|----------------------------------------------------------------------------------------------------------|
| `name`          | Unique identifier for your image. The final image will be `ghcr.io/kubeflow/pipelines-components-<name>` |
| `containerfile` | Path to your Containerfile relative to repo root                                                         |
| `context`       | Build context directory (usually the component directory)                                                |

**Naming convention:**
- Use lowercase with hyphens: `my-training-component`
- Be descriptive: `sklearn-preprocessing`, `pytorch-training`
- The full image path will be: `ghcr.io/kubeflow/pipelines-components-my-training-component`

### Step 3: Reference the Image in Your Component

In your `component.py`, use the `base_image` parameter with the `:main` tag:

```python
from kfp import dsl

@dsl.component(
    base_image="ghcr.io/kubeflow/pipelines-components-my-training-component:main"
)
def my_component(input_path: str) -> str:
    import pandas as pd
    import sklearn
    
    # Your component logic here
    ...
```

**Important:** Always use the `:main` tag during development. This ensures:
- Your component uses the latest image from the main branch
- PR validation can override the tag to test against PR-built images

### Step 4: Update metadata.yaml (Optional)

Document the base image in your component's `metadata.yaml`:

```yaml
tier: core
name: my_component
stability: alpha
base_image: ghcr.io/kubeflow/pipelines-components-my-training-component:main
dependencies:
  kubeflow:
    - name: Pipelines
      version: '>=2.5'
```

### How CI Handles Base Images

| Event                        | Behavior                                                                           |
|------------------------------|------------------------------------------------------------------------------------|
| Pull Request                 | Images are built but **not pushed**. Validation runs against locally-built images. |
| Push to `main`               | Images are built and pushed with tags: `:main`, `:<sha>`                           |
| Push to tag (e.g., `v1.0.0`) | Images are built and pushed with tags: `:<tag>`, `:<sha>`                          |

### Image Tags

Your image will be available with these tags:

| Tag         | Description                   | Example                              |
|-------------|-------------------------------|--------------------------------------|
| `:main`     | Latest build from main branch | `...-my-component:main`              |
| `:<sha>`    | Specific commit (full SHA)    | `...-my-component:abc123def456...`   |
| `:<branch>` | Branch name                   | `...-my-component:feature-x`         |
| `:<tag>`    | Git tag                       | `...-my-component:v1.0.0`            |

### Testing Your Image Locally

Before submitting a PR, test your image locally:

```bash
# Build the image
podman build -t my-component:test -f components/training/my_component/Containerfile components/training/my_component

# Test it
podman run --rm my-component:test python -c "import pandas; print(pandas.__version__)"
```

## Submitting Your Contribution

### Commit Your Changes

Use descriptive commit messages following the [Conventional Commits](https://conventionalcommits.org/) format:

```bash
git add .
git status  # Review what you're committing
git diff --cached  # Check the actual changes

git commit -m "feat(training): add <my_component> training component

- Implements <my_component> Core-Tier component
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

- **Governance questions**: See [GOVERNANCE.md](GOVERNANCE.md) for tier requirements and processes
- **Community discussion**: Join `#kubeflow-pipelines` channel on the [CNCF Slack](https://www.kubeflow.org/docs/about/community/#kubeflow-slack-channels)
- **Bug reports and feature requests**: Open an issue at [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues)

---

This repository was established through [KEP-913: Components Repository](https://github.com/kubeflow/community/tree/master/proposals/913-components-repo).

Thanks for contributing to Kubeflow Pipelines! 🚀
