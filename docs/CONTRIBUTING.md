# Contributing to Kubeflow Pipelines Components

Welcome! This guide covers how to contribute components to the Kubeflow Pipelines Components Repository.

## Table of Contents

- [Quick Start](#quick-start)
- [What We Accept](#what-we-accept)
- [Component Structure](#component-structure)
- [Required Files](#required-files)
- [Development Workflow](#development-workflow)
- [Testing Requirements](#testing-requirements)
- [Review Process](#review-process)
- [Before Submitting](#before-submitting)
- [Getting Help](#getting-help)
- [Naming Conventions](#naming-conventions)
- [References](#references)

## Quick Start

*Get up and running with your first contribution in 7 simple steps.*

1. **Read the [Kubeflow Community Code of Conduct](https://github.com/kubeflow/community/blob/master/CODE_OF_CONDUCT.md)** - All contributors must follow these guidelines
2. **Fork and clone** the repository
3. **Set up environment** - see [ONBOARDING.md](ONBOARDING.md)
4. **Create feature branch** - `git checkout -b component/my-component`
5. **Develop component** following the structure below
6. **Test thoroughly** - see [TESTING.md](TESTING.md)
7. **Submit pull request**

## What We Accept

*Types of contributions we welcome to the repository.*

- **Individual Components**: ML tasks (preprocessing, training, evaluation)
- **Component Collections**: Related component sets
- **Pipeline Templates**: Complete pipeline examples
- **Bug Fixes**: Improvements to existing components

## Component Structure

*Standard directory layout and files required for every component.*

Each component must follow this structure:

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

## Required Files

*Essential files that every component must include with examples.*

### metadata.yaml

```yaml
name: my_component
description: Brief description
version: 1.0.0
inputs:
  - name: input_data
    type: Dataset
    description: Input dataset
outputs:
  - name: output_data
    type: Dataset
    description: Output dataset
image: gcr.io/project/my-component:1.0.0
```

### README.md

Must include:
- Component overview
- Input/output specifications  
- Usage examples
- Configuration options

### OWNERS

```yaml
approvers:
  - maintainer1
reviewers:
  - reviewer1
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

## Development Workflow

*Step-by-step process from setup to pull request submission.*

### 1. Initial Setup

```bash
# Fork the repository on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/pipeline-components.git
cd pipeline-components

# Add upstream remote to sync with main repository
git remote add upstream https://github.com/kubeflow/pipeline-components.git

# Verify remotes are set up correctly
git remote -v
```

### 2. Environment Setup

```bash
# Set up development environment (see ONBOARDING.md for details)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync --dev

# Install pre-commit hooks for code quality
pre-commit install

# Verify setup works
./scripts/lint.sh
pytest
```

### 3. Create Feature Branch

```bash
# Always sync with upstream before creating new branches
git fetch upstream
git checkout main
git merge upstream/main

# Create descriptive feature branch
git checkout -b component/data-preprocessing
# or for bug fixes:
git checkout -b fix/issue-123
```

### 4. Implement Your Component

Create your component following the required structure:

```bash
# Create component directory
mkdir -p components/my_component/{src,tests}

# Create required files
touch components/my_component/metadata.yaml
touch components/my_component/README.md
touch components/my_component/OWNERS
touch components/my_component/Containerfile  # required only for custom images
touch components/my_component/src/{main.py,requirements.txt}
touch components/my_component/tests/test_main.py
```

**Implementation checklist:**
- [ ] Write component logic in `src/main.py`
- [ ] Define dependencies in `src/requirements.txt`
- [ ] Create comprehensive `metadata.yaml`
- [ ] Write detailed `README.md` with examples
- [ ] Add maintainers to `OWNERS` file
- [ ] Build efficient `Containerfile` (only if custom images required)

### 5. Test Your Component

Thoroughly test your component before submitting. See [TESTING.md](TESTING.md) for detailed testing guidelines and commands.

**Quick test checklist:**
- [ ] Run `./scripts/lint.sh` for code quality checks
- [ ] Run `pytest --cov=src` for unit tests with coverage
- [ ] Build and test your container image
- [ ] Verify component works with sample data

### 6. Commit Your Changes

```bash
# Stage your changes
git add .

# Check what you're committing
git status
git diff --cached

# Commit with descriptive message following Conventional Commits
git commit -m "feat: add data preprocessing component

- Implements StandardScaler and MinMaxScaler
- Adds comprehensive unit and integration tests
- Includes usage examples and documentation
- Resolves #123"

# For bug fixes:
git commit -m "fix: resolve memory leak in data loader

- Fix buffer overflow in large dataset processing
- Add memory usage tests
- Update documentation with memory requirements
- Fixes #456"
```

### 7. Push and Create Pull Request

```bash
# Push to your fork
git push origin component/my_component

# If this is your first push for this branch:
git push --set-upstream origin component/my_component
```

**Create PR on GitHub:**
1. Navigate to your fork on GitHub
2. Click "Compare & pull request" button
3. Fill out the PR template:
   - **Title**: Clear, descriptive title
   - **Description**: What does this PR do?
   - **Testing**: How was this tested?
   - **Checklist**: Complete the provided checklist
   - **Related Issues**: Link to relevant issues


## Testing Requirements

*Minimum testing standards all components must meet.*

- **Unit tests**: Test individual functions
- **Integration tests**: Test end-to-end functionality  
- **Coverage**: Minimum 80%
- **Error handling**: Test failure scenarios

See [TESTING.md](TESTING.md) for detailed testing guidelines.

## Review Process

*How contributions are reviewed and what criteria they must meet.*

All PRs must pass:
- Automated checks (linting, tests, builds)
- Code review by maintainers
- Documentation review

### Review Criteria

- Component works as described
- Code is clean and well-documented
- Tests provide good coverage
- Follows repository standards

## Before Submitting

*Final checklist to ensure your contribution is ready for review.*

- [ ] Component builds successfully
- [ ] All tests pass (≥80% coverage)
- [ ] All required files present
- [ ] Documentation complete
- [ ] Follows naming conventions
- [ ] No security vulnerabilities

## Getting Help

*Resources and channels for getting support during development.*

- **Setup**: [ONBOARDING.md](ONBOARDING.md)
- **Testing**: [TESTING.md](TESTING.md)
- **Governance**: [GOVERNANCE.md](GOVERNANCE.md)
- **Best Practices**: [BESTPRACTICES.md](BESTPRACTICES.md) *(coming soon)*
- **Agents**: [AGENTS.md](AGENTS.md) *(coming soon)*
- **Community**: `#kubeflow-pipelines` channel on the [CNCF Slack](https://www.kubeflow.org/docs/about/community/#kubeflow-slack-channels)
- **Issues**: [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues) for bugs/features

## Naming Conventions

*Standardized naming patterns for components, branches, and commits.*

- **Components**: `snake_case` (e.g., `data_preprocessing`)
- **Branches**: `component/name` or `fix/issue-123`
- **Commits**: Follow [Conventional Commits](https://conventionalcommits.org/)

---

## References

This repository was established through [KEP-913: Components Repository](https://github.com/kubeflow/community/tree/master/proposals/913-components-repo).

Thanks for contributing! 🚀
