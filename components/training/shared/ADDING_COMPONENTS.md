# Adding New Fine-Tuning Components

This guide helps you add new fine-tuning components (e.g., LoRA, QLoRA, etc.) to this subcategory.

## Structure

New components should follow this structure:

```
components/training/finetuning/<algorithm_name>/
├── __init__.py
├── component.py
├── metadata.yaml
├── OWNERS
├── README.md
└── tests/
    └── test_component_unit.py
```

## Using Shared Utilities

All fine-tuning components can use utilities from `../shared/`. The shared utilities are organized in `shared/finetuning_utils.py` and re-exported through `shared/__init__.py`:

```python
from kfp_components.components.training.shared import (
    configure_env,           # Environment variable configuration
    create_logger,           # Logger setup
    download_oci_model,      # OCI model downloads
    extract_metrics_from_jsonl,  # Training metrics extraction
    init_k8s,               # Kubernetes client initialization
    parse_kv,               # Parse key=value strings
    persist_model,          # Save model to PVC and artifacts
    plot_training_loss,     # Generate loss chart
    prepare_jsonl,          # Convert dataset to JSONL
    resolve_dataset,        # Resolve dataset from HF/S3/PVC
    setup_hf_token,         # HuggingFace token configuration
)
```

The shared module structure follows the Kubeflow Pipelines subcategory pattern:

```
shared/
├── __init__.py           # Exports shared utilities
└── finetuning_utils.py   # Utility function implementations
```

## Component Template

### 1. component.py

```python
@dsl.component(
    base_image="quay.io/opendatahub/odh-training-th04-cpu-torch29-py312-rhel9:cpu-3.3",
    packages_to_install=[
        "kubernetes",
        "olot",
        "matplotlib",
        "kfp-components@git+https://github.com/red-hat-data-services/pipelines-components.git@main",
    ],
)
def train_model(
    pvc_path: str,
    output_model: dsl.Output[dsl.Model],
    output_metrics: dsl.Output[dsl.Metrics],
    output_loss_chart: dsl.Output[dsl.HTML],
    # Add algorithm-specific parameters here
) -> str:
    \"\"\"Train model using <ALGORITHM>. Outputs model artifact and metrics.\"\"\"
    from kfp_components.components.training.shared import (
        create_logger,
        init_k8s,
        configure_env,
        resolve_dataset,
        persist_model,
        # Import what you need
    )

    log = create_logger("train_model")
    log.info(f"Initializing <ALGORITHM> training component")

    # Use shared utilities as needed
    # ...
```

### 2. metadata.yaml

```yaml
name: <algorithm_name>
stability: alpha
dependencies:
  kubeflow:
    - name: Pipelines
      version: '>=2.15.2'
    - name: Trainer
      version: '>=0.1.0'
  external_services:
    - name: HuggingFace Datasets
      version: ">=2.14.0"
    - name: Kubernetes
      version: ">=1.28.0"
tags:
  - training
  - fine_tuning
  - <algorithm_name>
  - llm
lastVerified: YYYY-MM-DDT00:00:00Z
links:
  documentation: https://github.com/kubeflow/trainer
```

### 3. README.md

Include an "Installation & Usage" section:

```markdown
## Installation & Usage

This component uses shared utilities from the parent `kfp-components` package.
The component automatically installs the package at runtime via:

\```python
packages_to_install=[
    "kfp-components@git+https://github.com/red-hat-data-services/pipelines-components.git@main"
]
\```
```

## Update pyproject.toml

Add your component package:

```toml
"kfp_components.components.training.finetuning.<algorithm_name>",
```

## Update Subcategory README

Add your component to `components/training/finetuning/README.md`:

```markdown
- **[<ALGORITHM>](<algorithm_name>/)** - <Short description>
```

## Examples

See existing components for reference:

- `osft/` - OSFT with mini-trainer backend
- `sft/` - SFT with instructlab-training backend
