# SDG Hub Component

Runs [SDG Hub](https://github.com/Red-Hat-AI-Innovation-Team/sdg_hub) synthetic data generation flows as a Kubeflow Pipelines component.

## Overview

This component wraps the SDG Hub SDK to execute composable data generation flows within KFP pipelines. It supports:

- Built-in flows via `flow_id` (from the SDG Hub registry)
- Custom flows via `flow_yaml_path` (mounted from ConfigMap or PVC)
- Automatic LLM model configuration for flows with LLM blocks
- Checkpointing for resumable execution

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_artifact` | `dsl.Input[dsl.Dataset]` | `None` | KFP Dataset artifact from upstream component |
| `input_pvc_path` | `str` | `""` | Path to JSONL input file on a mounted PVC |
| `flow_id` | `str` | `""` | Built-in flow ID from the SDG Hub registry |
| `flow_yaml_path` | `str` | `""` | Path to a custom flow YAML file |
| `model` | `str` | `""` | LiteLLM model identifier (e.g. `openai/gpt-4o-mini`) |
| `max_concurrency` | `int` | `10` | Maximum concurrent LLM requests |
| `checkpoint_pvc_path` | `str` | `""` | PVC path for checkpoints |
| `save_freq` | `int` | `100` | Checkpoint save frequency |
| `log_level` | `str` | `"INFO"` | Logging level |
| `temperature` | `float` | `0.7` | LLM sampling temperature |
| `max_tokens` | `int` | `2048` | Maximum response tokens |
| `export_to_pvc` | `bool` | `False` | Export output to PVC (in addition to KFP artifact) |
| `export_path` | `str` | `""` | Base PVC path for exports (required if `export_to_pvc` is `True`) |

## Outputs

- `output_artifact` (`Dataset`): JSONL file with generated data
- `output_metrics` (`Metrics`): JSON with `input_rows`, `output_rows`, `execution_time_seconds`

## Usage

### Basic PVC Input

```python
from components.sdg.sdg_hub import sdg
from kfp import dsl
from kfp_kubernetes import mount_pvc, use_secret_as_env

@dsl.pipeline(name="sdg-pipeline")
def my_pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_id="green-clay-812",
        model="openai/gpt-4o-mini",
    )

    # Mount PVC containing input data
    mount_pvc(
        task=sdg_task,
        pvc_name="data-pvc",
        mount_path="/mnt/data",
    )

    # Inject LLM API credentials
    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"OPENAI_APIKEY": "LLM_API_KEY"},
    )
```

### Artifact Chaining

Chain SDG with upstream components by consuming their output artifacts:

```python
from components.sdg.sdg_hub import sdg
from kfp import dsl
from kfp_kubernetes import use_secret_as_env

@dsl.component(packages_to_install=["pandas"])
def preprocess_data(output_data: dsl.Output[dsl.Dataset]) -> None:
    import pandas as pd
    # ... preprocessing logic ...
    df.to_json(output_data.path, orient="records", lines=True)

@dsl.pipeline(name="sdg-chained-pipeline")
def chained_pipeline():
    # Step 1: Preprocess data
    preprocess_task = preprocess_data()

    # Step 2: Run SDG using preprocessed data
    sdg_task = sdg(
        input_artifact=preprocess_task.outputs["output_data"],
        flow_id="green-clay-812",
        model="openai/gpt-4o-mini",
    )

    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"OPENAI_APIKEY": "LLM_API_KEY"},
    )
```

### PVC Export

Export generated data to a PVC for archival or external access:

```python
from components.sdg.sdg_hub import sdg
from kfp import dsl
from kfp_kubernetes import mount_pvc, use_secret_as_env

@dsl.pipeline(name="sdg-export-pipeline")
def export_pipeline():
    sdg_task = sdg(
        input_pvc_path="/mnt/data/input.jsonl",
        flow_id="green-clay-812",
        model="openai/gpt-4o-mini",
        export_to_pvc=True,
        export_path="/mnt/data/exports",
    )

    # Mount PVC for both input and export
    mount_pvc(
        task=sdg_task,
        pvc_name="data-pvc",
        mount_path="/mnt/data",
    )

    use_secret_as_env(
        task=sdg_task,
        secret_name="llm-credentials",
        secret_key_to_env={"OPENAI_APIKEY": "LLM_API_KEY"},
    )
```

Exports are saved to: `{export_path}/{flow_id}/{timestamp}/generated.jsonl`

## Local Development

### Prerequisites

```bash
# From the repo root
uv venv && source .venv/bin/activate
uv sync --extra test
```

### Running the Component Locally

KFP's `LocalRunner` does not support `Input[Dataset]` artifacts, so local execution
calls `sdg.python_func()` directly with mock artifact objects.

A ready-to-run script is provided at `run_local.py`:

```bash
cd components/sdg/sdg_hub
LLM_API_KEY="<your-api-key>" python run_local.py
```

This runs the LLM test flow against `test_data/sdg_hub/sample_input.jsonl` using
`gpt-4o-mini`, prints the generated output, and cleans up the temp directory.

To run with your own data or flow:

```python
import json
import os
import tempfile

import pandas as pd

from components.sdg.sdg_hub.component import sdg


class Artifact:
    def __init__(self, path):
        self.path = path


with tempfile.TemporaryDirectory() as tmp_dir:
    output_artifact = Artifact(os.path.join(tmp_dir, "output.jsonl"))
    output_metrics = Artifact(os.path.join(tmp_dir, "metrics.json"))

    sdg.python_func(
        output_artifact=output_artifact,
        output_metrics=output_metrics,
        input_pvc_path="/path/to/your/input.jsonl",
        flow_yaml_path="/path/to/your/flow.yaml",  # or use flow_id="green-clay-812"
        model="openai/gpt-4o-mini",
        max_concurrency=1,
        temperature=0.7,
        max_tokens=2048,
        checkpoint_pvc_path="",
        save_freq=100,
        log_level="INFO",
        export_to_pvc=False,
        export_path="",
    )

    # Read results
    df = pd.read_json(output_artifact.path, lines=True)
    print(df)

    with open(output_metrics.path) as f:
        print(json.dumps(json.load(f), indent=2))
```

To persist output to a local directory instead of a temp folder, set
`export_to_pvc=True` and `export_path` to a local directory. Output is written to
`{export_path}/{flow_id}/{timestamp}/generated.jsonl`.

### Running Tests

```bash
# Unit tests (no API key needed)
pytest components/sdg/sdg_hub/tests/test_component_unit.py -v

# Integration test with transform-only flow (no API key needed)
pytest components/sdg/sdg_hub/tests/test_component_local.py::TestSdgHubLocalRunner -v

# LLM E2E tests (requires API key)
LLM_API_KEY="<your-api-key>" pytest components/sdg/sdg_hub/tests/test_component_local.py::TestSdgHubLLMFlow -v
```

## Environment Variables

For flows with LLM blocks, set these via Kubernetes Secrets:

- `LLM_API_KEY`: API key for the LLM provider
- `LLM_API_BASE`: API base URL (optional, for self-hosted models)
