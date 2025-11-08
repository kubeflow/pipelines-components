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


## Development Workflow

See the [developer onboarding guide](ONBOARDING.md) for steps and guidence on developing and contributing a new component or pipeline to this repository


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
