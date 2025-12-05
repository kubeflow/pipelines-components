# Kubeflow Pipelines Components Repository

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)

Welcome to the official Kubeflow Pipelines Components repository! This is the centralized hub for reusable components and pipelines within the Kubeflow ecosystem, providing a structured collection of AI workflow building blocks for Kubernetes.

## 🎯 Purpose

The Kubeflow Pipelines Components repository serves as:

- **Centralized Asset Library**: A dedicated space for hosting reusable components and pipelines, promoting consistency and ease of access across the Kubeflow ecosystem
- **Standardized Documentation Hub**: Ensuring each component and pipeline includes comprehensive documentation and metadata for better discoverability and usability
- **Community Collaboration Platform**: Providing clear guidelines and governance to encourage contributions from the community
- **Automated Quality Assurance**: Implementing automated testing and maintenance processes to ensure reliability and up-to-date status of all assets

## 📦 Repository Structure

```
├── components/ # Core reusable components
│   ├── <component category>/
│   ├── <component category>/
│   └── <component category>/
│
├── pipelines/ # Complete AI pipelines
│   ├── <component category>/
│   ├── <component category>/
│   └── <component category>/
│
├── third_party/         # Third-party contributions
│   ├── components/      # Third-party components
│   └── pipelines/       # Third-party pipelines
│
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

### Component Categories

- **Training**: Components for model training, hyperparameter tuning, and optimization
- **Evaluation**: Model evaluation, metrics calculation, and performance analysis
- **Data Processing**: Data preparation, transformation, and feature engineering
- **Deployment**: Model serving, endpoint management, and production deployment

## 🚀 Installation

> ⚠️ **Work in Progress**: This repository is currently under development. The packages described below are not yet available on PyPI. This section outlines the planned installation process for when the packages are released.

### Prerequisites

- Python 3.11 or later
- Kubeflow Pipelines SDK

### Install Core Components (Coming Soon)

Install the official Kubeflow SDK with components:

```bash
# Not yet available - coming soon!
pip install kubeflow
```

### Install Third-Party Components (Coming Soon)

For vetted third-party contributions:

```bash
# Not yet available - coming soon!
pip install kfp-components-third-party
```

### Verify Installation

Once the packages are available, you'll be able to verify the installation:

```python
# Coming soon - example verification code
from kubeflow.pipelines.components import training, evaluation, data_processing

# Example: Use a training component
from kubeflow.pipelines.components.training import my_component

# List available components
print(dir(training))
```

## 💻 Usage

### Using Components in Your Pipeline

```python
from kfp import dsl
from kubeflow.pipelines.components.training import model_trainer
from kubeflow.pipelines.components.evaluation import model_evaluator

@dsl.pipeline(
    name="my-ai-pipeline",
    description="Example pipeline using KFP components"
)
def my_pipeline(
    dataset_path: str,
    model_name: str
):
    # Train model using a reusable component
    training_task = model_trainer(
        dataset=dataset_path,
        model_name=model_name
    )
    
    # Evaluate the trained model
    evaluation_task = model_evaluator(
        model=training_task.outputs["model"],
        test_dataset=dataset_path
    )
```

### Component Metadata

Each component includes standardized metadata:

- **Tier**: `core` (community-maintained) or `third_party`
- **Stability**: `alpha`, `beta`, or `stable`
- **Dependencies**: Kubeflow and external service requirements
- **Last Verified**: Date of last verification
- **Documentation**: Links to detailed documentation

## 📚 Documentation

### Core Documentation

- [Component Specification](https://www.kubeflow.org/docs/components/pipelines/concepts/component/): Detailed information on component structure and definition
- [Creating Components](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/): Guidelines for authoring new components
- [Pipeline Concepts](https://www.kubeflow.org/docs/components/pipelines/concepts/pipeline/): Overview of pipelines in Kubeflow

### Repository Documentation

- [Onboarding Guide](docs/ONBOARDING.md): Getting started for new contributors
- [Contributing Guidelines](docs/CONTRIBUTING.md): How to contribute components and pipelines
- [Best Practices](docs/BESTPRACTICES.md): Component authoring best practices
- [Governance](docs/GOVERNANCE.md): Repository governance and tier system
- [Agent Guidelines](docs/AGENTS.md): Guidance for code-generation agents

## 🤝 Contributing

We welcome contributions from the community! To contribute:

1. **Review Guidelines**: Read our [Contributing Guidelines](docs/CONTRIBUTING.md)
2. **Choose a Tier**: Decide between core (community-maintained) or third-party contribution
3. **Follow Standards**: Ensure your component includes:
   - `component.py` or `pipeline.py` - The implementation
   - `metadata.yaml` - Standardized metadata
   - `README.md` - Component documentation
   - `OWNERS` - Maintainer information
   - `tests/` - Unit tests
   - `example_pipelines.py` - Usage examples

4. **Submit PR**: Open a pull request with your contribution

### Quality Standards

All contributions must:
- Pass linting and formatting checks (Black, pydocstyle)
- Include comprehensive docstrings
- Compile successfully with `kfp.compiler`
- Include metadata with fresh `lastVerified` date
- Pass automated CI/CD checks

## 🔧 Maintenance

### Automated Maintenance

The repository includes automated maintenance processes:

- **Verification Reminders**: Components are flagged when `lastVerified` is older than 9 months
- **Dependency Updates**: Dependabot monitors and suggests dependency updates
- **Security Scanning**: Critical CVEs trigger automated remediation PRs
- **Removal Process**: Components not verified within 12 months are proposed for removal

### Component Ownership

Each component has designated owners listed in its `OWNERS` file who:
- Review and approve changes
- Update metadata and verification status
- Manage component lifecycle
- Respond to issues and questions

## 📦 Releases

- **Core Package**: `kubeflow` - Official Kubeflow SDK including community-maintained components
- **Third-Party Package**: `kfp-components-third-party` - Vetted third-party contributions
- **Versioning**: Follows semantic versioning aligned with Kubeflow releases
- **Release Cadence**: Regular releases aligned with Kubeflow Pipelines SDK

## 🔗 Links

- [Kubeflow Website](https://www.kubeflow.org/)
- [Kubeflow Pipelines](https://github.com/kubeflow/pipelines)
- [Issue Tracker](https://github.com/kubeflow/pipelines-components/issues)
- [Community Slack](https://kubeflow.slack.com/)
- [Mailing List](https://groups.google.com/g/kubeflow-discuss)

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

## 🙏 Acknowledgments

Thank you to all contributors and the Kubeflow community for making this repository possible!

---

*For questions, issues, or suggestions, please open an issue in our [GitHub repository](https://github.com/kubeflow/pipelines-components/issues) or reach out on the [Kubeflow Slack](https://kubeflow.slack.com/).*