# KFP Components Third-Party

Community-contributed third-party components for Kubeflow Pipelines, not maintained by Kubeflow SIGs.

## Overview

This package contains third-party components and pipelines contributed by the Kubeflow community. These components are not officially maintained by Kubeflow SIGs but are provided as community contributions.

## Installation

```bash
pip install kfp-components-third-party
```

## Usage

Import third-party components and pipelines from this package:

```python
from kubeflow.pipelines.components.third_party import components, pipelines
from kubeflow.pipelines.components.third_party.components import training, evaluation, data_processing, deployment
from kubeflow.pipelines.components.third_party.pipelines import training, evaluation, data_processing, deployment

# For example:
from kubeflow.pipelines.components.third_party.components.training import my_training_component
from kubeflow.pipelines.components.third_party.pipelines.evaluation import my_evaluation_pipeline
```

## Contributing

For contribution guidelines, please see the main repository's [CONTRIBUTING.md](https://github.com/kubeflow/pipelines-components/blob/main/docs/CONTRIBUTING.md).

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](https://github.com/kubeflow/pipelines-components/blob/main/LICENSE) file for details.

## Support

These are community-contributed components and are not officially supported by Kubeflow SIGs. For issues and questions, please use the [GitHub Issues](https://github.com/kubeflow/pipelines-components/issues) page.
